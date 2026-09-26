import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.models import GestorAccess, RoleEnum, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = decode_access_token(token)
        return {"email": payload["sub"], "role": payload["role"]}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o caducado",
        )


def get_current_db_user(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    owner = db.query(User).filter(User.email == user["email"]).first()
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
    return owner


def get_target_owner(
    cliente_id: Optional[uuid.UUID] = Query(default=None, description="Solo gestores: cliente cuyos datos se consultan"),
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Dueño de los datos que se van a LEER: el propio usuario, o un cliente si el
    usuario es gestor con acceso aceptado. Solo debe usarse en endpoints de lectura;
    los de escritura usan siempre get_current_db_user, así un gestor nunca modifica
    datos de un cliente. Cualquier caso no permitido responde 404 para no revelar
    qué usuarios existen.
    """
    if cliente_id is None or cliente_id == user.id:
        return user

    tiene_acceso = (
        user.role == RoleEnum.gestor
        and db.query(GestorAccess)
        .filter(
            GestorAccess.owner_id == cliente_id,
            GestorAccess.gestor_id == user.id,
            GestorAccess.estado == "aceptado",
        )
        .first()
        is not None
    )
    cliente = db.get(User, cliente_id) if tiene_acceso else None
    if not cliente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return cliente


def require_role(*allowed_roles: str):
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para esta acción",
            )
        return user

    return checker
