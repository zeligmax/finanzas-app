from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.models import User

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


def require_role(*allowed_roles: str):
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para esta acción",
            )
        return user

    return checker
