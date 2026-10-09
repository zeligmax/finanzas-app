import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_db_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.models import RoleEnum, User
from app.services.email import enviar_correo_verificacion

router = APIRouter(prefix="/api/auth", tags=["auth"])

VALIDEZ_VERIFICACION = timedelta(hours=48)
COOLDOWN_REENVIO = timedelta(seconds=60)


class RegisterIn(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    es_gestor: bool = False


class VerifyOut(BaseModel):
    verificado: bool
    mensaje: str


def _enviar_verificacion(user: User, db: Session) -> None:
    user.verificacion_codigo = secrets.token_urlsafe(32)
    user.verificacion_expira = datetime.utcnow() + VALIDEZ_VERIFICACION
    db.commit()

    enlace = f"{settings.FRONTEND_URL.rstrip('/')}/verificar?token={user.verificacion_codigo}"
    enviar_correo_verificacion(user.email, user.full_name, enlace)


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")

    token = create_access_token(subject=user.email, role=user.role.value)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Usuario ya existe")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=RoleEnum.gestor if payload.es_gestor else RoleEnum.team,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _enviar_verificacion(user, db)

    token = create_access_token(subject=user.email, role=user.role.value)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/verify/{token}", response_model=VerifyOut)
def verificar_correo(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verificacion_codigo == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Enlace no válido o ya usado")
    if user.verificacion_expira and user.verificacion_expira < datetime.utcnow():
        raise HTTPException(status_code=400, detail="El enlace ha caducado. Pide que te reenvíen el correo")

    user.email_verificado = True
    user.verificacion_codigo = None
    user.verificacion_expira = None
    db.commit()
    return VerifyOut(verificado=True, mensaje="Correo confirmado.")


@router.post("/resend-verification", response_model=VerifyOut)
def reenviar_verificacion(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_db_user),
):
    if user.email_verificado:
        return VerifyOut(verificado=True, mensaje="Tu correo ya estaba confirmado.")

    if user.verificacion_expira:
        emitido_en = user.verificacion_expira - VALIDEZ_VERIFICACION
        if datetime.utcnow() - emitido_en < COOLDOWN_REENVIO:
            raise HTTPException(status_code=429, detail="Espera un momento antes de pedir otro correo.")

    _enviar_verificacion(user, db)
    return VerifyOut(verificado=False, mensaje="Te hemos enviado un nuevo enlace de confirmación.")
