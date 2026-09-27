import time
import uuid
from collections import defaultdict, deque
from dataclasses import asdict

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_db_user
from app.db.session import get_db
from app.models.models import DocumentoPendiente, RoleEnum, User
from app.schemas.builder import SubidaOut
from app.services.invoice_parser import analizar_texto
from app.services.ocr import CONFIANZA_MINIMA, ErrorLectura, MAX_BYTES, leer_texto

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Límite por usuario para que una cuenta no pueda saturar el servidor con subidas seguidas.
MAX_SUBIDAS = 20
VENTANA_SEGUNDOS = 10 * 60
_subidas: dict[uuid.UUID, deque] = defaultdict(deque)


def _comprobar_limite(usuario_id: uuid.UUID) -> None:
    ahora = time.monotonic()
    marcas = _subidas[usuario_id]
    while marcas and ahora - marcas[0] > VENTANA_SEGUNDOS:
        marcas.popleft()
    if len(marcas) >= MAX_SUBIDAS:
        raise HTTPException(status_code=429, detail="Demasiadas subidas seguidas. Espera unos minutos.")
    marcas.append(ahora)


def _serializable(datos: dict) -> dict:
    """El resultado del analizador trae un date; JSON no lo admite tal cual."""
    datos = dict(datos)
    if datos.get("fecha"):
        datos["fecha"] = datos["fecha"].isoformat()
    return datos


@router.post("/upload", response_model=SubidaOut, status_code=201)
def subir_documento(
    file: UploadFile = File(...),
    tipo: str = Form(...),
    db: Session = Depends(get_db),
    usuario: User = Depends(get_current_db_user),
):
    """
    Sube un PDF o una imagen de factura para que la revise un Builder. No se muestra
    ningún dato al usuario aquí: se analiza en el servidor y la revisión humana se
    hace en la cola de Builder. Al aprobarse, la factura/gasto se crea solo en la
    cuenta del usuario.
    """
    if usuario.role in (RoleEnum.gestor, RoleEnum.builder):
        raise HTTPException(status_code=403, detail="Esta cuenta no puede subir documentos")
    if tipo not in ("ingreso", "gasto"):
        raise HTTPException(status_code=400, detail="tipo debe ser 'ingreso' o 'gasto'")

    _comprobar_limite(usuario.id)
    contenido = file.file.read(MAX_BYTES + 1)

    try:
        lectura = leer_texto(contenido)
    except ErrorLectura as e:
        raise HTTPException(status_code=e.estado, detail=e.mensaje)

    resultado = analizar_texto(lectura.texto, usuario.nif)
    datos = _serializable(asdict(resultado))
    if lectura.confianza is not None and lectura.confianza < CONFIANZA_MINIMA:
        datos["avisos"].insert(
            0,
            "La imagen se ha leído con poca fiabilidad (borrosa, torcida o con mucho ruido): revísalo con cuidado.",
        )

    doc = DocumentoPendiente(
        owner_id=usuario.id,
        tipo=tipo,
        nombre_archivo=file.filename or "documento",
        tipo_archivo=file.content_type or "application/octet-stream",
        archivo=contenido,
        datos_extraidos=datos,
        estado="pendiente",
    )
    db.add(doc)
    db.commit()

    return SubidaOut(
        mensaje="Recibido. Una persona lo revisará y, en menos de 24 h, la factura estará en tu cuenta."
    )
