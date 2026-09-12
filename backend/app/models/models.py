import enum
import uuid
from datetime import date

from sqlalchemy import Boolean, Column, Date, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class RoleEnum(str, enum.Enum):
    owner = "owner"
    team = "team"
    gestor = "gestor"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(Enum(RoleEnum), default=RoleEnum.team, nullable=False)
    is_active = Column(Boolean, default=True)


class Invoice(Base):
    """Factura emitida (venta)."""

    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    numero = Column(String, nullable=False)
    fecha = Column(Date, nullable=False, default=date.today)
    cliente_nombre = Column(String, nullable=False)
    cliente_nif = Column(String, nullable=True)

    base_imponible = Column(Float, nullable=False, default=0.0)
    tipo_iva = Column(Float, nullable=False, default=21.0)  # 0 si está exenta
    exenta_iva = Column(Boolean, default=False)
    motivo_exencion = Column(String, nullable=True)  # ej. "formación", "sanidad"

    retencion_irpf_pct = Column(Float, nullable=False, default=0.0)  # 0, 7 o 15 normalmente

    cobrada = Column(Boolean, default=False)
    fecha_cobro = Column(Date, nullable=True)

    archivo_url = Column(String, nullable=True)  # PDF/imagen subido

    @property
    def cuota_iva(self) -> float:
        return 0.0 if self.exenta_iva else self.base_imponible * self.tipo_iva / 100

    @property
    def retencion_importe(self) -> float:
        return self.base_imponible * self.retencion_irpf_pct / 100

    @property
    def total(self) -> float:
        return self.base_imponible + self.cuota_iva - self.retencion_importe


class Expense(Base):
    """Gasto / factura recibida."""

    __tablename__ = "expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    fecha = Column(Date, nullable=False, default=date.today)
    proveedor_nombre = Column(String, nullable=False)
    proveedor_nif = Column(String, nullable=True)
    categoria = Column(String, nullable=False)  # ej. "suministros", "software", "dietas"

    base_imponible = Column(Float, nullable=False, default=0.0)
    tipo_iva = Column(Float, nullable=False, default=21.0)
    iva_deducible = Column(Boolean, default=True)

    pagado = Column(Boolean, default=False)
    fecha_pago = Column(Date, nullable=True)

    archivo_url = Column(String, nullable=True)

    @property
    def cuota_iva(self) -> float:
        return self.base_imponible * self.tipo_iva / 100
