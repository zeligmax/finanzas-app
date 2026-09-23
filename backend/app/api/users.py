from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_db_user
from app.db.session import get_db
from app.models.models import User
from app.schemas.user import UserProfileOut, UserProfileUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserProfileOut)
def obtener_perfil(owner: User = Depends(get_current_db_user)):
    return owner


@router.put("/me", response_model=UserProfileOut)
def actualizar_perfil(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_db_user),
):
    owner.full_name = (payload.full_name or "").strip() or None
    owner.nif = (payload.nif or "").strip().upper() or None
    owner.cuota_autonomos_mensual = payload.cuota_autonomos_mensual
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner
