import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ExpenseCreate(BaseModel):
    numero_factura: Optional[str] = None
    fecha: date

    proveedor_nombre: str
    proveedor_nif: Optional[str] = None

    pagador_nombre: Optional[str] = None
    pagador_nif: Optional[str] = None

    categoria: str
    base_imponible: float
    tipo_iva: float = 21.0
    retencion_irpf_pct: float = 0.0


class ExpenseOut(ExpenseCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    cuota_iva: float
    retencion_importe: float
