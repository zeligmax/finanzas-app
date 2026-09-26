import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_db_user, get_target_owner
from app.db.session import get_db
from app.models.models import Invoice, User
from app.schemas.invoice import InvoiceCreate, InvoiceOut

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("/", response_model=List[InvoiceOut])
def listar_facturas(
    db: Session = Depends(get_db),
    owner: User = Depends(get_target_owner),
):
    return (
        db.query(Invoice)
        .filter(Invoice.owner_id == owner.id)
        .order_by(Invoice.fecha.desc())
        .all()
    )


@router.post("/", response_model=InvoiceOut, status_code=201)
def crear_factura(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_db_user),
):
    factura = Invoice(owner_id=owner.id, **payload.model_dump())
    db.add(factura)
    db.commit()
    db.refresh(factura)
    return factura


def _factura_propia(db: Session, owner: User, factura_id: uuid.UUID) -> Invoice:
    factura = db.query(Invoice).filter(Invoice.id == factura_id, Invoice.owner_id == owner.id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return factura


@router.put("/{factura_id}", response_model=InvoiceOut)
def editar_factura(
    factura_id: uuid.UUID,
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_db_user),
):
    factura = _factura_propia(db, owner, factura_id)
    for campo, valor in payload.model_dump().items():
        setattr(factura, campo, valor)
    db.commit()
    db.refresh(factura)
    return factura


@router.delete("/{factura_id}", status_code=204)
def borrar_factura(
    factura_id: uuid.UUID,
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_db_user),
):
    db.delete(_factura_propia(db, owner, factura_id))
    db.commit()
