import uuid
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


class ContactoCreate(BaseModel):
    tipo: Literal["cliente", "proveedor"]
    nombre: str
    nif: Optional[str] = None
    direccion: Optional[str] = None


class ContactoOut(ContactoCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
