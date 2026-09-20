from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.models import Expense, Invoice, User
from app.services.tax_calculator import (
    ResultadoModelo130,
    calcular_iva_trimestral,
    calcular_modelo_130,
    calcular_renta_anual,
)

router = APIRouter(prefix="/api/taxes", tags=["taxes"])


def _owner_id(db: Session, user: dict):
    owner = db.query(User).filter(User.email == user["email"]).first()
    return owner.id if owner else None


def _validar_trimestre(trimestre: int) -> None:
    if trimestre not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="El trimestre debe ser 1, 2, 3 o 4")


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
    _validar_trimestre(trimestre)
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


def _modelo130_acumulado(
    db: Session, owner_id, anio: int, hasta_trimestre: int
) -> list[tuple[int, ResultadoModelo130]]:
    """
    Calcula el modelo 130 de cada trimestre desde el 1 hasta `hasta_trimestre`,
    encadenando los acumulados reales (rendimiento neto, retenciones y pagos
    fraccionados ya ingresados) trimestre a trimestre.
    """
    resultados: list[tuple[int, ResultadoModelo130]] = []
    rendimiento_neto_acumulado = 0.0
    retenciones_acumuladas = 0.0
    pagos_fraccionados_ingresados = 0.0

    for trimestre in range(1, hasta_trimestre + 1):
        facturas = _facturas_trimestre(db, owner_id, anio, trimestre)
        gastos = _gastos_trimestre(db, owner_id, anio, trimestre)

        ingresos = sum(f.base_imponible for f in facturas)
        gastos_total = sum(g.base_imponible for g in gastos)
        retenciones_trimestre = sum(f.retencion_importe for f in facturas)

        resultado = calcular_modelo_130(
            ingresos_trimestre=ingresos,
            gastos_trimestre=gastos_total,
            rendimiento_neto_acumulado_anterior=rendimiento_neto_acumulado,
            retenciones_trimestre=retenciones_trimestre,
            retenciones_acumuladas_anterior=retenciones_acumuladas,
            pagos_fraccionados_ingresados_anio=pagos_fraccionados_ingresados,
        )
        resultados.append((trimestre, resultado))

        rendimiento_neto_acumulado = resultado.rendimiento_neto_acumulado
        retenciones_acumuladas += retenciones_trimestre
        pagos_fraccionados_ingresados += resultado.resultado

    return resultados


@router.get("/modelo130/{anio}/{trimestre}")
def modelo_130(
    anio: int,
    trimestre: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _validar_trimestre(trimestre)
    owner_id = _owner_id(db, user)
    resultados = _modelo130_acumulado(db, owner_id, anio, trimestre)
    return resultados[-1][1]


@router.get("/modelo130/{anio}")
def modelo_130_anual(
    anio: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Los 4 modelos 130 del año, encadenados con sus acumulados reales."""
    owner_id = _owner_id(db, user)
    resultados = _modelo130_acumulado(db, owner_id, anio, 4)
    return [{"trimestre": t, **asdict(r)} for t, r in resultados]


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

    pagos_fraccionados_anuales = sum(
        r.resultado for _, r in _modelo130_acumulado(db, owner_id, anio, 4)
    )

    resultado = calcular_renta_anual(
        rendimiento_neto_anual=ingresos - gastos_total,
        retenciones_anuales=retenciones,
        pagos_fraccionados_anuales=pagos_fraccionados_anuales,
    )
    return resultado
