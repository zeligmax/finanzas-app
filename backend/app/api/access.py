import secrets
import uuid
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_db_user
from app.db.session import get_db
from app.models.models import GestorAccess, RoleEnum, User
from app.schemas.access import AccessOut, ClienteOut, GestorInfo, InvitationCreate, RedeemIn

# Sin caracteres ambiguos (0/O, 1/I/L) para que el código se pueda dictar o copiar sin errores.
ALFABETO_CODIGO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LONGITUD_CODIGO = 10
VALIDEZ_INVITACION = timedelta(days=7)

owner_router = APIRouter(prefix="/api/access", tags=["access"])
gestor_router = APIRouter(prefix="/api/gestor", tags=["gestor"])


def _nuevo_codigo() -> str:
    return "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(LONGITUD_CODIGO))


def _normalizar(codigo: str) -> str:
    return "".join(c for c in codigo.upper() if c.isalnum())


def _exigir_gestor(user: User) -> None:
    if user.role != RoleEnum.gestor:
        raise HTTPException(status_code=403, detail="Solo las cuentas de gestor pueden hacer esto")


# ---------------------------------------------------------------------------
# Lado del dueño de los datos
# ---------------------------------------------------------------------------

@owner_router.post("/invitations", response_model=AccessOut, status_code=201)
def crear_invitacion(
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_db_user),
):
    if owner.role == RoleEnum.gestor:
        raise HTTPException(status_code=403, detail="Una cuenta de gestor no puede invitar a otros gestores")

    acceso = GestorAccess(
        owner_id=owner.id,
        codigo=_nuevo_codigo(),
        etiqueta=(payload.etiqueta or "").strip() or None,
        estado="pendiente",
        expires_at=datetime.utcnow() + VALIDEZ_INVITACION,
    )
    db.add(acceso)
    db.commit()
    db.refresh(acceso)
    return _acceso_out(acceso, None)


@owner_router.get("/", response_model=List[AccessOut])
def listar_accesos(
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_db_user),
):
    accesos = (
        db.query(GestorAccess)
        .filter(GestorAccess.owner_id == owner.id)
        .order_by(GestorAccess.created_at.desc())
        .all()
    )
    gestores = {g.id: g for g in db.query(User).filter(User.id.in_([a.gestor_id for a in accesos if a.gestor_id])).all()}
    return [_acceso_out(a, gestores.get(a.gestor_id)) for a in accesos]


@owner_router.delete("/{acceso_id}", status_code=204)
def revocar_acceso(
    acceso_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_db_user),
):
    """Cancela una invitación o revoca un acceso. Pueden hacerlo el dueño y el propio gestor."""
    acceso = db.get(GestorAccess, acceso_id)
    if not acceso or user.id not in (acceso.owner_id, acceso.gestor_id):
        raise HTTPException(status_code=404, detail="Acceso no encontrado")
    db.delete(acceso)
    db.commit()


def _acceso_out(acceso: GestorAccess, gestor: User | None) -> AccessOut:
    return AccessOut(
        id=acceso.id,
        etiqueta=acceso.etiqueta,
        estado=acceso.estado,
        codigo=acceso.codigo if acceso.estado == "pendiente" else None,
        expires_at=acceso.expires_at,
        created_at=acceso.created_at,
        gestor=GestorInfo(nombre=gestor.full_name, email=gestor.email) if gestor else None,
    )


# ---------------------------------------------------------------------------
# Lado del gestor
# ---------------------------------------------------------------------------

@gestor_router.post("/redeem", response_model=ClienteOut)
def canjear_codigo(
    payload: RedeemIn,
    db: Session = Depends(get_db),
    gestor: User = Depends(get_current_db_user),
):
    _exigir_gestor(gestor)

    acceso = (
        db.query(GestorAccess)
        .filter(GestorAccess.codigo == _normalizar(payload.codigo), GestorAccess.estado == "pendiente")
        .first()
    )
    if not acceso or acceso.expires_at < datetime.utcnow():
        raise HTTPException(status_code=404, detail="Código no válido o caducado")

    ya_vinculado = (
        db.query(GestorAccess)
        .filter(
            GestorAccess.owner_id == acceso.owner_id,
            GestorAccess.gestor_id == gestor.id,
            GestorAccess.estado == "aceptado",
        )
        .first()
    )
    if ya_vinculado:
        raise HTTPException(status_code=400, detail="Ya tienes acceso a este cliente")

    acceso.gestor_id = gestor.id
    acceso.estado = "aceptado"
    db.commit()
    return _cliente_out(acceso, db.get(User, acceso.owner_id))


@gestor_router.get("/clients", response_model=List[ClienteOut])
def listar_clientes(
    db: Session = Depends(get_db),
    gestor: User = Depends(get_current_db_user),
):
    _exigir_gestor(gestor)
    accesos = (
        db.query(GestorAccess)
        .filter(GestorAccess.gestor_id == gestor.id, GestorAccess.estado == "aceptado")
        .order_by(GestorAccess.created_at.desc())
        .all()
    )
    clientes = {u.id: u for u in db.query(User).filter(User.id.in_([a.owner_id for a in accesos])).all()}
    return [_cliente_out(a, clientes[a.owner_id]) for a in accesos]


def _cliente_out(acceso: GestorAccess, cliente: User) -> ClienteOut:
    return ClienteOut(
        acceso_id=acceso.id,
        cliente_id=cliente.id,
        nombre=cliente.full_name,
        email=cliente.email,
        nif=cliente.nif,
        desde=acceso.created_at,
    )
