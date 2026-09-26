from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class ParteOut(BaseModel):
    nif: Optional[str] = None
    nombre: Optional[str] = None
    nif_valido: Optional[bool] = None


class ExtraccionOut(BaseModel):
    metodo: str  # "texto_pdf" (sin OCR) | "ocr"
    tipo: Optional[str] = None  # "ingreso" | "gasto" | None si no se puede saber
    numero: Optional[str] = None
    fecha: Optional[date] = None
    emisor: ParteOut
    receptor: ParteOut
    base_imponible: Optional[float] = None
    tipo_iva: Optional[float] = None
    retencion_irpf_pct: Optional[float] = None
    total: Optional[float] = None
    avisos: List[str] = []
    texto: str = ""
