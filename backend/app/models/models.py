import enum
import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Column, Date, DateTime, Enum, Float, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class RoleEnum(str, enum.Enum):
    owner = "owner"
    team = "team"
    gestor = "gestor"
    builder = "builder"  # personal interno: revisa y corrige las facturas que suben los usuarios


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    nif = Column(String, nullable=True)
    direccion = Column(String, nullable=True)  # dirección fiscal, para precargar el emisor en facturas nuevas
    cuota_autonomos_mensual = Column(Float, nullable=False, default=0.0, server_default="0")
    role = Column(Enum(RoleEnum), default=RoleEnum.team, nullable=False)
    is_active = Column(Boolean, default=True)


class GestorAccess(Base):
    """
    Acceso de solo lectura de un gestor a los datos de un usuario.

    El dueño crea una invitación (estado "pendiente") con un código de un solo uso
    que comparte con su gestor. Al canjearlo, pasa a "aceptado" y se rellena gestor_id.
    """

    __tablename__ = "gestor_access"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    gestor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    codigo = Column(String, unique=True, index=True, nullable=False)
    etiqueta = Column(String, nullable=True)
    estado = Column(String, nullable=False, default="pendiente")  # "pendiente" | "aceptado"
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


class DocumentoPendiente(Base):
    """
    Un PDF/imagen que un usuario ha subido para que un Builder lo revise.

    El usuario solo lo envía: no ve el resultado del análisis. Un Builder lo revisa,
    corrige los datos que hagan falta y, al aprobarlo, se crea automáticamente la
    factura o el gasto en la cuenta del usuario. El archivo se guarda en la base de
    datos (bytea) solo mientras está pendiente; se borra al aprobar o rechazar.
    """

    __tablename__ = "documentos_pendientes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    tipo = Column(String, nullable=False)  # "ingreso" | "gasto", elegido por el usuario al subir
    nombre_archivo = Column(String, nullable=False)
    tipo_archivo = Column(String, nullable=False)  # mime type
    archivo = Column(LargeBinary, nullable=True)  # se borra al aprobar/rechazar

    datos_extraidos = Column(JSON, nullable=True)  # lo que detectó el analizador, de partida

    estado = Column(String, nullable=False, default="pendiente")  # "pendiente" | "aprobado" | "rechazado"
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    revisado_por = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    revisado_en = Column(DateTime, nullable=True)
    motivo_rechazo = Column(String, nullable=True)


class Contacto(Base):
    """
    Cliente o proveedor recurrente, guardado por el usuario para no volver a teclear
    su nombre/NIF cada vez. Es solo una plantilla de partida: al usarlo en una factura
    o gasto, sus datos se copian ahí (igual que emisor/cliente/proveedor ya funcionan),
    así que borrar o editar un contacto no afecta a los documentos ya creados.
    """

    __tablename__ = "contactos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    tipo = Column(String, nullable=False)  # "cliente" | "proveedor"
    nombre = Column(String, nullable=False)
    nif = Column(String, nullable=True)
    direccion = Column(String, nullable=True)


class Invoice(Base):
    """Factura emitida (venta)."""

    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    numero = Column(String, nullable=False)
    fecha = Column(Date, nullable=False, default=date.today)
    concepto = Column(String, nullable=True)  # descripción del servicio/producto, para el PDF

    # Pagador: quien paga la factura (el cliente)
    cliente_nombre = Column(String, nullable=False)
    cliente_nif = Column(String, nullable=True)
    cliente_direccion = Column(String, nullable=True)

    # Cobrador: quien la emite y cobra (el propio autónomo/empresa)
    emisor_nombre = Column(String, nullable=False)
    emisor_nif = Column(String, nullable=True)
    emisor_direccion = Column(String, nullable=True)

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
    numero_factura = Column(String, nullable=True)

    # Cobrador: quien emite la factura y cobra (el proveedor)
    proveedor_nombre = Column(String, nullable=False)
    proveedor_nif = Column(String, nullable=True)

    # Pagador: quien la paga (el propio autónomo/empresa)
    pagador_nombre = Column(String, nullable=True)
    pagador_nif = Column(String, nullable=True)

    categoria = Column(String, nullable=False)  # ej. "suministros", "software", "dietas"

    base_imponible = Column(Float, nullable=False, default=0.0)
    tipo_iva = Column(Float, nullable=False, default=21.0)
    iva_deducible = Column(Boolean, default=True)

    retencion_irpf_pct = Column(Float, nullable=False, default=0.0)  # IRPF que retiene el proveedor, si aplica

    pagado = Column(Boolean, default=False)
    fecha_pago = Column(Date, nullable=True)

    archivo_url = Column(String, nullable=True)

    @property
    def cuota_iva(self) -> float:
        return self.base_imponible * self.tipo_iva / 100

    @property
    def retencion_importe(self) -> float:
        return self.base_imponible * self.retencion_irpf_pct / 100
