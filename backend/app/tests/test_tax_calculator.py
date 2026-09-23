"""
Ejecutar con: pytest backend/app/tests/test_tax_calculator.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.tax_calculator import (
    calcular_iva_trimestral,
    calcular_modelo_130,
    calcular_renta_anual,
)


def test_iva_sin_exenciones():
    r = calcular_iva_trimestral(
        ventas_sujetas_base=12000,
        tipo_iva_ventas=21,
        ventas_exentas_base=0,
        compras_base=4000,
        tipo_iva_compras=21,
    )
    assert r.prorrata_pct == 100
    assert round(r.iva_devengado, 2) == 2520.0
    assert round(r.iva_soportado_deducible, 2) == 840.0
    assert round(r.resultado, 2) == 1680.0
    assert r.a_ingresar


def test_iva_con_exenciones_aplica_prorrata():
    r = calcular_iva_trimestral(
        ventas_sujetas_base=12000,
        tipo_iva_ventas=21,
        ventas_exentas_base=3000,
        compras_base=4000,
        tipo_iva_compras=21,
    )
    assert round(r.prorrata_pct, 2) == 80.0
    assert round(r.iva_soportado_deducible, 2) == 672.0  # 840 * 0.8


def test_modelo_130_no_es_negativo():
    r = calcular_modelo_130(
        ingresos_trimestre=5000,
        gastos_trimestre=4500,
        rendimiento_neto_acumulado_anterior=0,
        retenciones_trimestre=0,
        retenciones_acumuladas_anterior=0,
        pagos_fraccionados_ingresados_anio=1000,
    )
    assert r.resultado == 0.0  # nunca da derecho a devolución


def test_renta_anual_resultado_a_pagar():
    r = calcular_renta_anual(
        rendimiento_neto_anual=44000,
        retenciones_anuales=0,
        pagos_fraccionados_anuales=0,
    )
    assert r.base_liquidable == 44000.0
    assert r.cuota_integra > 0
    assert r.resultado == r.cuota_integra


def test_renta_anual_minimo_personal_se_descuenta_de_la_cuota_no_de_la_base():
    # Rendimiento 35.550 (Cataluña, la más cara en este tramo):
    #   impuesto de la base = 4.427,50 (estatal) + 4.619,50 (autonómica) = 9.047,00
    #   impuesto del mínimo = 5.550 * (9,5% + 9,5%)                      = 1.054,50
    r = calcular_renta_anual(35550, 0, 0)
    assert r.base_liquidable == 35550.0
    assert r.comunidad_referencia == "Cataluña"
    assert round(r.cuota_sobre_base, 2) == 9047.0
    assert round(r.reduccion_minimo_personal, 2) == 1054.5
    assert round(r.cuota_integra, 2) == 7992.5


def test_renta_anual_por_debajo_del_minimo_no_paga():
    r = calcular_renta_anual(5000, 0, 0)
    assert r.cuota_integra == 0.0
    assert r.comunidad_referencia == ""


def test_renta_anual_descuenta_cuota_de_autonomos():
    sin_cuota = calcular_renta_anual(44000, 0, 0)
    con_cuota = calcular_renta_anual(44000, 0, 0, cuota_autonomos_anual=3600)
    assert con_cuota.rendimiento_neto_tras_cuota == 40400
    assert con_cuota.base_liquidable == sin_cuota.base_liquidable - 3600
    assert con_cuota.cuota_integra < sin_cuota.cuota_integra


def test_renta_anual_tipo_medio():
    r = calcular_renta_anual(35550, 0, 0)
    assert round(r.tipo_medio_pct, 2) == round(r.cuota_integra / 35550 * 100, 2)
    assert 19 < r.tipo_medio_pct < 50

    perdidas = calcular_renta_anual(-1000, 0, 0)
    assert perdidas.tipo_medio_pct == 0.0
    assert perdidas.cuota_integra == 0.0
