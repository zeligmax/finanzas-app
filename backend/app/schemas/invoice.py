import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class InvoiceCreate(BaseModel):
    numero: str
    fecha: date

    cliente_nombre: str
    cliente_nif: Optional[str] = None

    emisor_nombre: str
    emisor_nif: Optional[str] = None

    base_imponible: float
    tipo_iva: float = 21.0
    retencion_irpf_pct: float = 0.0


class InvoiceOut(InvoiceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    cuota_iva: float
    retencion_importe: float
    total: float
