import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_db_user
from app.db.session import get_db
from app.models.models import Contacto, RoleEnum, User
from app.schemas.contacto import ContactoCreate, ContactoOut

router = APIRouter(prefix="/api/contactos", tags=["contactos"])


def _exigir_escritura(usuario: User) -> None:
    if usuario.role in (RoleEnum.gestor, RoleEnum.builder):
        raise HTTPException(status_code=403, detail="Esta cuenta no puede gestionar contactos")


@router.get("/", response_model=List[ContactoOut])
def listar_contactos(
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_db_user),
):
    consulta = db.query(Contacto).filter(Contacto.owner_id == owner.id)
    if tipo:
        consulta = consulta.filter(Contacto.tipo == tipo)
    return consulta.order_by(Contacto.nombre.asc()).all()


@router.post("/", response_model=ContactoOut, status_code=201)
def crear_contacto(
    payload: ContactoCreate,
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_db_user),
):
    _exigir_escritura(owner)
    contacto = Contacto(owner_id=owner.id, **payload.model_dump())
    db.add(contacto)
    db.commit()
    db.refresh(contacto)
    return contacto


def _contacto_propio(db: Session, owner: User, contacto_id: uuid.UUID) -> Contacto:
    contacto = db.query(Contacto).filter(Contacto.id == contacto_id, Contacto.owner_id == owner.id).first()
    if not contacto:
        raise HTTPException(status_code=404, detail="Contacto no encontrado")
    return contacto


@router.put("/{contacto_id}", response_model=ContactoOut)
def editar_contacto(
    contacto_id: uuid.UUID,
    payload: ContactoCreate,
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_db_user),
):
    _exigir_escritura(owner)
    contacto = _contacto_propio(db, owner, contacto_id)
    for campo, valor in payload.model_dump().items():
        setattr(contacto, campo, valor)
    db.commit()
    db.refresh(contacto)
    return contacto


@router.delete("/{contacto_id}", status_code=204)
def borrar_contacto(
    contacto_id: uuid.UUID,
    db: Session = Depends(get_db),
    owner: User = Depends(get_current_db_user),
):
    _exigir_escritura(owner)
    db.delete(_contacto_propio(db, owner, contacto_id))
    db.commit()
