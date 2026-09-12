"""
Motor de cálculo fiscal para autónomos en España.
Lógica validada en prototipo interactivo antes de implementarla aquí.

Cubre:
- IVA trimestral (modelo 303), con prorrata por operaciones exentas (art. 20 LIVA)
- IRPF pago fraccionado trimestral (modelo 130)
- Estimación de IRPF anual (declaración de la Renta, modelo 100)
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# IVA trimestral (modelo 303)
# ---------------------------------------------------------------------------

@dataclass
class ResultadoIVA:
    iva_devengado: float
    prorrata_pct: float
    iva_soportado_bruto: float
    iva_soportado_deducible: float
    resultado: float  # positivo = a ingresar, negativo = a compensar

    @property
    def a_ingresar(self) -> bool:
        return self.resultado >= 0


def calcular_iva_trimestral(
    ventas_sujetas_base: float,
    tipo_iva_ventas: float,
    ventas_exentas_base: float,
    compras_base: float,
    tipo_iva_compras: float,
) -> ResultadoIVA:
    """
    ventas_sujetas_base: suma de bases imponibles de facturas emitidas CON IVA
    ventas_exentas_base: suma de bases de facturas emitidas EXENTAS (formación, sanidad...)
    compras_base: suma de bases imponibles de gastos/facturas recibidas deducibles
    tipo_iva_*: en tanto por ciento (21, 10, 4)

    Si hay mezcla de ventas sujetas y exentas, se aplica la regla de prorrata:
    solo se puede deducir el IVA soportado en la proporción que representan
    las ventas sujetas sobre el total de ventas.
    """
    total_ventas = ventas_sujetas_base + ventas_exentas_base
    prorrata_pct = (ventas_sujetas_base / total_ventas * 100) if total_ventas > 0 else 100.0

    iva_devengado = ventas_sujetas_base * tipo_iva_ventas / 100
    iva_soportado_bruto = compras_base * tipo_iva_compras / 100
    iva_soportado_deducible = iva_soportado_bruto * (prorrata_pct / 100)

    resultado = iva_devengado - iva_soportado_deducible

    return ResultadoIVA(
        iva_devengado=iva_devengado,
        prorrata_pct=prorrata_pct,
        iva_soportado_bruto=iva_soportado_bruto,
        iva_soportado_deducible=iva_soportado_deducible,
        resultado=resultado,
    )


# ---------------------------------------------------------------------------
# IRPF - pago fraccionado trimestral (modelo 130)
# ---------------------------------------------------------------------------

PORCENTAJE_PAGO_FRACCIONADO = 0.20


@dataclass
class ResultadoModelo130:
    rendimiento_neto_trimestre: float
    rendimiento_neto_acumulado: float
    pago_fraccionado_bruto: float
    resultado: float  # nunca negativo (no da derecho a devolución)


def calcular_modelo_130(
    ingresos_trimestre: float,
    gastos_trimestre: float,
    rendimiento_neto_acumulado_anterior: float,
    retenciones_trimestre: float,
    retenciones_acumuladas_anterior: float,
    pagos_fraccionados_ingresados_anio: float,
) -> ResultadoModelo130:
    rendimiento_neto_trimestre = ingresos_trimestre - gastos_trimestre
    rendimiento_neto_acumulado = rendimiento_neto_acumulado_anterior + rendimiento_neto_trimestre

    pago_bruto = rendimiento_neto_acumulado * PORCENTAJE_PAGO_FRACCIONADO

    resultado = (
        pago_bruto
        - retenciones_acumuladas_anterior
        - retenciones_trimestre
        - pagos_fraccionados_ingresados_anio
    )
    resultado = max(resultado, 0.0)

    return ResultadoModelo130(
        rendimiento_neto_trimestre=rendimiento_neto_trimestre,
        rendimiento_neto_acumulado=rendimiento_neto_acumulado,
        pago_fraccionado_bruto=pago_bruto,
        resultado=resultado,
    )


# ---------------------------------------------------------------------------
# IRPF anual - estimación declaración de la Renta (modelo 100)
# ---------------------------------------------------------------------------

# Escala orientativa combinada (estatal + autonómica media). Ajustar según
# comunidad autónoma del usuario para una estimación más precisa.
TRAMOS_IRPF = [
    (12450, 0.19),
    (20200, 0.24),
    (35200, 0.30),
    (60000, 0.37),
    (300000, 0.45),
    (float("inf"), 0.47),
]

MINIMO_PERSONAL_DEFAULT = 5550.0


@dataclass
class ResultadoRentaAnual:
    base_liquidable: float
    cuota_integra: float
    resultado: float  # positivo = a pagar, negativo = a devolver

    @property
    def a_pagar(self) -> bool:
        return self.resultado >= 0


def _cuota_progresiva(base: float) -> float:
    cuota = 0.0
    anterior = 0.0
    for limite, tipo in TRAMOS_IRPF:
        if base > anterior:
            tramo_base = min(base, limite) - anterior
            cuota += tramo_base * tipo
            anterior = limite
        else:
            break
    return cuota


def calcular_renta_anual(
    rendimiento_neto_anual: float,
    retenciones_anuales: float,
    pagos_fraccionados_anuales: float,
    minimo_personal: float = MINIMO_PERSONAL_DEFAULT,
) -> ResultadoRentaAnual:
    """
    rendimiento_neto_anual: suma de los 4 trimestres (ingresos - gastos deducibles)
    retenciones_anuales: total de retenciones soportadas en el año
    pagos_fraccionados_anuales: suma de los 4 modelos 130 ingresados
    """
    base_liquidable = max(rendimiento_neto_anual - minimo_personal, 0.0)
    cuota_integra = _cuota_progresiva(base_liquidable)
    resultado = cuota_integra - retenciones_anuales - pagos_fraccionados_anuales

    return ResultadoRentaAnual(
        base_liquidable=base_liquidable,
        cuota_integra=cuota_integra,
        resultado=resultado,
    )
