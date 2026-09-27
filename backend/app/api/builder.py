import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_builder
from app.db.session import get_db
from app.models.models import DocumentoPendiente, Expense, Invoice, User
from app.schemas.builder import AprobarDocumentoIn, DocumentoPendienteOut, RechazarDocumentoIn, UsuarioBreve

router = APIRouter(prefix="/api/builder", tags=["builder"])


def _out(doc: DocumentoPendiente, usuario: User) -> DocumentoPendienteOut:
    return DocumentoPendienteOut(
        id=doc.id,
        tipo=doc.tipo,
        nombre_archivo=doc.nombre_archivo,
        tipo_archivo=doc.tipo_archivo,
        estado=doc.estado,
        creado_en=doc.creado_en,
        motivo_rechazo=doc.motivo_rechazo,
        usuario=UsuarioBreve(id=usuario.id, email=usuario.email, full_name=usuario.full_name, nif=usuario.nif),
        datos_extraidos=doc.datos_extraidos,
    )


def _documento_o_404(db: Session, doc_id: uuid.UUID) -> DocumentoPendiente:
    doc = db.get(DocumentoPendiente, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return doc


@router.get("/queue", response_model=List[DocumentoPendienteOut])
def listar_cola(
    estado: str = "pendiente",
    db: Session = Depends(get_db),
    builder: User = Depends(get_current_builder),
):
    documentos = (
        db.query(DocumentoPendiente, User)
        .join(User, User.id == DocumentoPendiente.owner_id)
        .filter(DocumentoPendiente.estado == estado)
        .order_by(DocumentoPendiente.creado_en.asc())
        .all()
    )
    return [_out(doc, usuario) for doc, usuario in documentos]


@router.get("/queue/{doc_id}", response_model=DocumentoPendienteOut)
def ver_documento(
    doc_id: uuid.UUID,
    db: Session = Depends(get_db),
    builder: User = Depends(get_current_builder),
):
    doc = _documento_o_404(db, doc_id)
    usuario = db.get(User, doc.owner_id)
    return _out(doc, usuario)


@router.get("/queue/{doc_id}/file")
def ver_archivo(
    doc_id: uuid.UUID,
    db: Session = Depends(get_db),
    builder: User = Depends(get_current_builder),
):
    doc = _documento_o_404(db, doc_id)
    if not doc.archivo:
        raise HTTPException(status_code=404, detail="El archivo ya no está disponible (documento ya revisado)")
    return Response(content=doc.archivo, media_type=doc.tipo_archivo)


@router.post("/queue/{doc_id}/approve", response_model=DocumentoPendienteOut)
def aprobar_documento(
    doc_id: uuid.UUID,
    payload: AprobarDocumentoIn,
    db: Session = Depends(get_db),
    builder: User = Depends(get_current_builder),
):
    doc = _documento_o_404(db, doc_id)
    if doc.estado != "pendiente":
        raise HTTPException(status_code=400, detail="Este documento ya se ha revisado")

    if doc.tipo == "ingreso":
        registro = Invoice(
            owner_id=doc.owner_id,
            numero=payload.numero,
            fecha=payload.fecha,
            cliente_nombre=payload.receptor.nombre,
            cliente_nif=payload.receptor.nif,
            emisor_nombre=payload.emisor.nombre,
            emisor_nif=payload.emisor.nif,
            base_imponible=payload.base_imponible,
            tipo_iva=payload.tipo_iva,
            retencion_irpf_pct=payload.retencion_irpf_pct,
        )
    else:
        if not payload.categoria:
            raise HTTPException(status_code=400, detail="Falta la categoría del gasto")
        registro = Expense(
            owner_id=doc.owner_id,
            numero_factura=payload.numero,
            fecha=payload.fecha,
            proveedor_nombre=payload.emisor.nombre,
            proveedor_nif=payload.emisor.nif,
            pagador_nombre=payload.receptor.nombre,
            pagador_nif=payload.receptor.nif,
            categoria=payload.categoria,
            base_imponible=payload.base_imponible,
            tipo_iva=payload.tipo_iva,
            retencion_irpf_pct=payload.retencion_irpf_pct,
        )
    db.add(registro)

    doc.estado = "aprobado"
    doc.archivo = None
    doc.revisado_por = builder.id
    doc.revisado_en = datetime.utcnow()
    db.commit()

    usuario = db.get(User, doc.owner_id)
    return _out(doc, usuario)


@router.post("/queue/{doc_id}/reject", response_model=DocumentoPendienteOut)
def rechazar_documento(
    doc_id: uuid.UUID,
    payload: RechazarDocumentoIn,
    db: Session = Depends(get_db),
    builder: User = Depends(get_current_builder),
):
    doc = _documento_o_404(db, doc_id)
    if doc.estado != "pendiente":
        raise HTTPException(status_code=400, detail="Este documento ya se ha revisado")

    doc.estado = "rechazado"
    doc.archivo = None
    doc.motivo_rechazo = payload.motivo
    doc.revisado_por = builder.id
    doc.revisado_en = datetime.utcnow()
    db.commit()

    usuario = db.get(User, doc.owner_id)
    return _out(doc, usuario)
