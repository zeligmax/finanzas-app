import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InvitationCreate(BaseModel):
    etiqueta: Optional[str] = Field(default=None, max_length=80)


class GestorInfo(BaseModel):
    nombre: Optional[str] = None
    email: str


class AccessOut(BaseModel):
    """Vista del dueño: sus invitaciones y gestores con acceso."""

    id: uuid.UUID
    etiqueta: Optional[str] = None
    estado: str
    codigo: Optional[str] = None  # solo mientras está pendiente
    expires_at: datetime
    created_at: datetime
    gestor: Optional[GestorInfo] = None


class RedeemIn(BaseModel):
    codigo: str


class ClienteOut(BaseModel):
    """Vista del gestor: un cliente que le ha dado acceso."""

    acceso_id: uuid.UUID
    cliente_id: uuid.UUID
    nombre: Optional[str] = None
    email: str
    nif: Optional[str] = None
    desde: datetime
