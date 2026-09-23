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

INF = float("inf")

# Escala estatal (igual para todas las comunidades de régimen común).
ESCALA_ESTATAL = [
    (12450, 0.095),
    (20200, 0.12),
    (35200, 0.15),
    (60000, 0.185),
    (300000, 0.225),
    (INF, 0.245),
]

# Escalas autonómicas (tramo superior del intervalo, tipo autonómico) de las
# comunidades más caras, ejercicio 2026. Se suman a la estatal sobre la misma
# base. El resto de comunidades (Andalucía, Galicia, Murcia, Castilla-La Mancha,
# Madrid, Castilla y León...) quedan por debajo de esta envolvente. No incluye
# Navarra ni País Vasco (régimen foral). Actualizar cada año.
ESCALAS_AUTONOMICAS = {
    "Comunidad Valenciana": [
        (12000, 0.088), (22000, 0.117), (32000, 0.146), (42000, 0.17),
        (52000, 0.194), (62000, 0.219), (72000, 0.244), (100000, 0.261),
        (150000, 0.2735), (200000, 0.2835), (INF, 0.2935),
    ],
    "Cataluña": [
        (12500, 0.095), (22000, 0.125), (33000, 0.16), (53000, 0.19),
        (90000, 0.215), (120000, 0.235), (175000, 0.245), (INF, 0.255),
    ],
    "Asturias": [
        (12450, 0.09), (17707, 0.12), (33007, 0.14), (53407, 0.192),
        (70000, 0.215), (90000, 0.225), (175000, 0.25), (INF, 0.26),
    ],
    "La Rioja": [
        (12450, 0.08), (20200, 0.106), (35200, 0.136), (40000, 0.178),
        (50000, 0.183), (60000, 0.19), (120000, 0.245), (INF, 0.27),
    ],
    "Aragón": [
        (13073, 0.095), (21210, 0.12), (36960, 0.15), (52500, 0.185),
        (60000, 0.205), (80000, 0.23), (90000, 0.24), (130000, 0.25), (INF, 0.255),
    ],
    "Canarias": [
        (13748, 0.09), (19422, 0.115), (35924, 0.14), (57566, 0.185),
        (93268, 0.235), (123745, 0.25), (INF, 0.26),
    ],
    "Extremadura": [
        (12450, 0.0775), (20200, 0.0975), (24200, 0.16), (35200, 0.175),
        (60000, 0.21), (80200, 0.235), (99200, 0.24), (120200, 0.245), (INF, 0.25),
    ],
    "Baleares": [
        (10000, 0.09), (18000, 0.1125), (30000, 0.1425), (48000, 0.175),
        (70000, 0.19), (90000, 0.2175), (120000, 0.2275), (175000, 0.2375), (INF, 0.2475),
    ],
    "Cantabria": [
        (13000, 0.085), (21000, 0.11), (35200, 0.145), (60000, 0.18),
        (90000, 0.225), (INF, 0.245),
    ],
}

MINIMO_PERSONAL_DEFAULT = 5550.0


@dataclass
class ResultadoRentaAnual:
    base_liquidable: float
    cuota_integra: float
    resultado: float  # positivo = a pagar, negativo = a devolver
    rendimiento_neto_tras_cuota: float = 0.0
    cuota_autonomos_anual: float = 0.0
    tipo_medio_pct: float = 0.0  # cuota íntegra / rendimiento neto tras cuota de autónomos
    comunidad_referencia: str = ""  # comunidad cuya escala da el peor caso
    cuota_sobre_base: float = 0.0  # impuesto de la base, antes del mínimo personal
    reduccion_minimo_personal: float = 0.0  # impuesto correspondiente al mínimo personal

    @property
    def a_pagar(self) -> bool:
        return self.resultado >= 0


def _cuota_progresiva(base: float, tramos: list) -> float:
    cuota = 0.0
    anterior = 0.0
    for limite, tipo in tramos:
        if base > anterior:
            tramo_base = min(base, limite) - anterior
            cuota += tramo_base * tipo
            anterior = limite
        else:
            break
    return cuota


def cuota_irpf_peor_caso(base: float, minimo_personal: float = 0.0) -> tuple[float, float, float, str]:
    """
    Cuota íntegra de la comunidad más cara para esa base.

    El mínimo personal no se resta de la base: se calcula el impuesto de la base
    y se descuenta el impuesto que corresponde al mínimo (misma escala).

    Devuelve (cuota_sobre_base, reduccion_minimo_personal, cuota_integra, comunidad).
    """
    if base <= 0:
        return 0.0, 0.0, 0.0, ""

    minimo = min(minimo_personal, base)
    mejor = (0.0, 0.0, 0.0, "")
    for comunidad, tramos in ESCALAS_AUTONOMICAS.items():
        cuota_base = _cuota_progresiva(base, ESCALA_ESTATAL) + _cuota_progresiva(base, tramos)
        reduccion = _cuota_progresiva(minimo, ESCALA_ESTATAL) + _cuota_progresiva(minimo, tramos)
        cuota_integra = cuota_base - reduccion
        if cuota_integra > mejor[2]:
            mejor = (cuota_base, reduccion, cuota_integra, comunidad)
    return mejor


def calcular_renta_anual(
    rendimiento_neto_anual: float,
    retenciones_anuales: float,
    pagos_fraccionados_anuales: float,
    minimo_personal: float = MINIMO_PERSONAL_DEFAULT,
    cuota_autonomos_anual: float = 0.0,
) -> ResultadoRentaAnual:
    """
    rendimiento_neto_anual: ingresos - gastos deducibles del año, antes de la cuota de autónomos
    retenciones_anuales: total de retenciones soportadas en el año
    pagos_fraccionados_anuales: suma de los 4 modelos 130 ingresados
    cuota_autonomos_anual: cotización a la Seguridad Social del año (gasto deducible)

    La cuota se calcula con la escala de la comunidad autónoma más cara (peor caso).
    """
    rendimiento_tras_cuota = rendimiento_neto_anual - cuota_autonomos_anual
    base_liquidable = max(rendimiento_tras_cuota, 0.0)
    cuota_base, reduccion_minimo, cuota_integra, comunidad = cuota_irpf_peor_caso(
        base_liquidable, minimo_personal
    )
    resultado = cuota_integra - retenciones_anuales - pagos_fraccionados_anuales
    tipo_medio = cuota_integra / rendimiento_tras_cuota * 100 if rendimiento_tras_cuota > 0 else 0.0

    return ResultadoRentaAnual(
        base_liquidable=base_liquidable,
        cuota_integra=cuota_integra,
        resultado=resultado,
        rendimiento_neto_tras_cuota=rendimiento_tras_cuota,
        cuota_autonomos_anual=cuota_autonomos_anual,
        tipo_medio_pct=tipo_medio,
        comunidad_referencia=comunidad,
        cuota_sobre_base=cuota_base,
        reduccion_minimo_personal=reduccion_minimo,
    )
