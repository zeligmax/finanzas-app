import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_db_user, get_target_owner
from app.db.session import get_db
from app.models.models import Expense, User
from app.schemas.expense import ExpenseCreate, ExpenseOut

router = APIRouter(prefix="/api/expenses", tags=["expenses"])


@router.get("/", response_model=List[ExpenseOut])
def listar_gastos(
    db: Session = Depends(get_db),
    owner: User = Depends(get_target_owner),
):
    return (
        db.query(Expense)
        .filter(Expense.owner_id == owner.id)
        .order_by(Expense.fecha.desc())
        .all()
    )


@router.post("/", response_model=ExpenseOut, status_code=201)
def crear_gasto(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_db_user),
):
    gasto = Expense(owner_id=owner.id, **payload.model_dump())
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    return gasto


def _gasto_propio(db: Session, owner: User, gasto_id: uuid.UUID) -> Expense:
    gasto = db.query(Expense).filter(Expense.id == gasto_id, Expense.owner_id == owner.id).first()
    if not gasto:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")
    return gasto


@router.put("/{gasto_id}", response_model=ExpenseOut)
def editar_gasto(
    gasto_id: uuid.UUID,
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_db_user),
):
    gasto = _gasto_propio(db, owner, gasto_id)
    for campo, valor in payload.model_dump().items():
        setattr(gasto, campo, valor)
    db.commit()
    db.refresh(gasto)
    return gasto


@router.delete("/{gasto_id}", status_code=204)
def borrar_gasto(
    gasto_id: uuid.UUID,
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_db_user),
):
    db.delete(_gasto_propio(db, owner, gasto_id))
    db.commit()
