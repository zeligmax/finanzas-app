from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.models import Expense, Invoice, User
from app.services.tax_calculator import (
    calcular_iva_trimestral,
    calcular_modelo_130,
    calcular_renta_anual,
)

router = APIRouter(prefix="/api/taxes", tags=["taxes"])


def _owner_id(db: Session, user: dict):
    owner = db.query(User).filter(User.email == user["email"]).first()
    return owner.id if owner else None


def _facturas_trimestre(db: Session, owner_id, anio: int, trimestre: int):
    mes_inicio = (trimestre - 1) * 3 + 1
    mes_fin = mes_inicio + 2
    return (
        db.query(Invoice)
        .filter(
            Invoice.owner_id == owner_id,
            extract("year", Invoice.fecha) == anio,
            extract("month", Invoice.fecha) >= mes_inicio,
            extract("month", Invoice.fecha) <= mes_fin,
        )
        .all()
    )


def _gastos_trimestre(db: Session, owner_id, anio: int, trimestre: int):
    mes_inicio = (trimestre - 1) * 3 + 1
    mes_fin = mes_inicio + 2
    return (
        db.query(Expense)
        .filter(
            Expense.owner_id == owner_id,
            extract("year", Expense.fecha) == anio,
            extract("month", Expense.fecha) >= mes_inicio,
            extract("month", Expense.fecha) <= mes_fin,
        )
        .all()
    )


@router.get("/iva/{anio}/{trimestre}")
def iva_trimestral(
    anio: int,
    trimestre: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    owner_id = _owner_id(db, user)
    facturas = _facturas_trimestre(db, owner_id, anio, trimestre)
    gastos = _gastos_trimestre(db, owner_id, anio, trimestre)

    ventas_sujetas = sum(f.base_imponible for f in facturas if not f.exenta_iva)
    ventas_exentas = sum(f.base_imponible for f in facturas if f.exenta_iva)
    tipo_medio_ventas = (
        sum(f.base_imponible * f.tipo_iva for f in facturas if not f.exenta_iva) / ventas_sujetas
        if ventas_sujetas
        else 0
    )

    compras_deducibles = sum(g.base_imponible for g in gastos if g.iva_deducible)
    tipo_medio_compras = (
        sum(g.base_imponible * g.tipo_iva for g in gastos if g.iva_deducible) / compras_deducibles
        if compras_deducibles
        else 0
    )

    resultado = calcular_iva_trimestral(
        ventas_sujetas_base=ventas_sujetas,
        tipo_iva_ventas=tipo_medio_ventas,
        ventas_exentas_base=ventas_exentas,
        compras_base=compras_deducibles,
        tipo_iva_compras=tipo_medio_compras,
    )
    return resultado


@router.get("/modelo130/{anio}/{trimestre}")
def modelo_130(
    anio: int,
    trimestre: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # Simplificado: en producción, acumular trimestres anteriores reales
    owner_id = _owner_id(db, user)
    facturas = _facturas_trimestre(db, owner_id, anio, trimestre)
    gastos = _gastos_trimestre(db, owner_id, anio, trimestre)

    ingresos = sum(f.base_imponible for f in facturas)
    gastos_total = sum(g.base_imponible for g in gastos)
    retenciones = sum(f.retencion_importe for f in facturas)

    resultado = calcular_modelo_130(
        ingresos_trimestre=ingresos,
        gastos_trimestre=gastos_total,
        rendimiento_neto_acumulado_anterior=0,  # TODO: sumar trimestres previos
        retenciones_trimestre=retenciones,
        retenciones_acumuladas_anterior=0,
        pagos_fraccionados_ingresados_anio=0,
    )
    return resultado


@router.get("/renta/{anio}")
def renta_anual(
    anio: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    owner_id = _owner_id(db, user)
    facturas = (
        db.query(Invoice)
        .filter(Invoice.owner_id == owner_id, extract("year", Invoice.fecha) == anio)
        .all()
    )
    gastos = (
        db.query(Expense)
        .filter(Expense.owner_id == owner_id, extract("year", Expense.fecha) == anio)
        .all()
    )

    ingresos = sum(f.base_imponible for f in facturas)
    gastos_total = sum(g.base_imponible for g in gastos)
    retenciones = sum(f.retencion_importe for f in facturas)

    resultado = calcular_renta_anual(
        rendimiento_neto_anual=ingresos - gastos_total,
        retenciones_anuales=retenciones,
        pagos_fraccionados_anuales=0,  # TODO: sumar los 4 modelos 130 reales
    )
    return resultado
