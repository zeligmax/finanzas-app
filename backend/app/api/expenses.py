from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_db_user
from app.db.session import get_db
from app.models.models import Expense, User
from app.schemas.expense import ExpenseCreate, ExpenseOut

router = APIRouter(prefix="/api/expenses", tags=["expenses"])


@router.get("/", response_model=List[ExpenseOut])
def listar_gastos(
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_db_user),
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
