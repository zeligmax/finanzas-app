import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SubidaOut(BaseModel):
    mensaje: str


class UsuarioBreve(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    nif: Optional[str] = None


class DocumentoPendienteOut(BaseModel):
    id: uuid.UUID
    tipo: str
    nombre_archivo: str
    tipo_archivo: str
    estado: str
    creado_en: datetime
    motivo_rechazo: Optional[str] = None
    usuario: UsuarioBreve
    datos_extraidos: Optional[Dict[str, Any]] = None


class ParteIn(BaseModel):
    nombre: str
    nif: Optional[str] = None


class AprobarDocumentoIn(BaseModel):
    numero: str
    fecha: date
    emisor: ParteIn
    receptor: ParteIn
    base_imponible: float
    tipo_iva: float = 21.0
    retencion_irpf_pct: float = 0.0
    categoria: Optional[str] = None  # obligatorio si el documento es de tipo "gasto"


class RechazarDocumentoIn(BaseModel):
    motivo: Optional[str] = None
