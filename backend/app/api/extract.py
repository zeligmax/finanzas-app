import time
import uuid
from collections import defaultdict, deque
from dataclasses import asdict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.deps import get_current_db_user
from app.models.models import RoleEnum, User
from app.schemas.extract import ExtraccionOut
from app.services.invoice_parser import analizar_texto
from app.services.ocr import CONFIANZA_MINIMA, ErrorLectura, MAX_BYTES, leer_texto

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Límite por usuario para que una cuenta no pueda saturar el servidor con lecturas seguidas.
MAX_LECTURAS = 20
VENTANA_SEGUNDOS = 10 * 60
_lecturas: dict[uuid.UUID, deque] = defaultdict(deque)


def _comprobar_limite(usuario_id: uuid.UUID) -> None:
    ahora = time.monotonic()
    marcas = _lecturas[usuario_id]
    while marcas and ahora - marcas[0] > VENTANA_SEGUNDOS:
        marcas.popleft()
    if len(marcas) >= MAX_LECTURAS:
        raise HTTPException(status_code=429, detail="Demasiadas lecturas seguidas. Espera unos minutos.")
    marcas.append(ahora)


@router.post("/extract", response_model=ExtraccionOut)
def extraer_datos_de_factura(
    file: UploadFile = File(...),
    usuario: User = Depends(get_current_db_user),
):
    """
    Lee un PDF o una imagen de factura y devuelve los campos detectados para que el
    usuario los revise. No guarda nada: ni el archivo ni el documento.
    """
    if usuario.role == RoleEnum.gestor:
        raise HTTPException(status_code=403, detail="Las cuentas de gestor son de solo lectura")

    _comprobar_limite(usuario.id)
    contenido = file.file.read(MAX_BYTES + 1)

    try:
        lectura = leer_texto(contenido)
    except ErrorLectura as e:
        raise HTTPException(status_code=e.estado, detail=e.mensaje)

    datos = asdict(analizar_texto(lectura.texto, usuario.nif))
    if lectura.confianza is not None and lectura.confianza < CONFIANZA_MINIMA:
        datos["avisos"].insert(
            0,
            "La imagen se ha leído con poca fiabilidad (borrosa, torcida o con mucho ruido): revisa todos los campos. "
            "Una foto más nítida o el PDF original darán mejor resultado.",
        )
    return ExtraccionOut(metodo=lectura.metodo, texto=lectura.visible[:6000], **datos)
