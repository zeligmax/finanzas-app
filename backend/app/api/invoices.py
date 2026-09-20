from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_db_user
from app.db.session import get_db
from app.models.models import Invoice, User
from app.schemas.invoice import InvoiceCreate, InvoiceOut

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("/", response_model=List[InvoiceOut])
def listar_facturas(
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_db_user),
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
