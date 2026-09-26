import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.invoice_parser import _parse_importe, analizar_texto
from app.services.nif import nif_cif_valido, normalizar_nif

# NIFs válidos: DNI 12345678Z, CIFs B12345674 y A58818501
USUARIO = "12345678Z"

FACTURA_ES_INGRESO = """
FACTURA
Nº Factura: F-2026-001
Fecha: 15/03/2026        Vencimiento: 15/04/2026

EMISOR
Juan Pérez García
C/ Mayor 5, 08001 Barcelona
NIF: 12345678Z

FACTURAR A
Cliente Ejemplo S.L.
Avda. Diagonal 100, 08019 Barcelona
CIF: B12345674

Concepto              Cantidad     Precio      Importe
Desarrollo web            1      1.000,00     1.000,00

Base imponible        1.000,00 €
IVA 21%                 210,00 €
Retención IRPF -15%    -150,00 €
TOTAL FACTURA         1.060,00 €
"""

FACTURA_CA_GASTO = """
FACTURA
Factura núm.: 2026/0045
Data: 3 de març de 2026
Data venciment: 2 d'abril de 2026

Proveïdor:
Subministraments Catalans S.A.
Carrer de Balmes 20, 08007 Barcelona
NIF: A58818501

Client:
Joan Martí Puig
NIF 12345678Z

Descripció                 Import
Material d'oficina         200,00
Base imposable          200,00 €
IVA (21%)                42,00 €
Total factura           242,00 €
"""

FACTURA_EN_GASTO = """
INVOICE
Invoice No: INV-2026-118
Invoice date: March 12, 2026
Due date: April 11, 2026

From:
Acme Software Ltd
VAT: ESB12345674

Bill to:
Maria Lopez
NIF: 12345678Z

Subtotal   500.00
VAT 21%    105.00
Total due  605.00
"""

FACTURA_TABLA = """
Factura F-77
Fecha de emisión: 01/02/2026
Empresa Demo SL
CIF B12345674
Cliente: Pedro Ruiz
NIF 12345678Z
Base imponible   % IVA   Cuota IVA   Total
800,00           21%     168,00      968,00
"""

FACTURA_VARIOS_IVA = """
Factura nº 10
Fecha 10/01/2026
Empresa Demo SL
CIF B12345674
Cliente: Pedro Ruiz
NIF 12345678Z
Base imponible 21%   100,00
IVA 21%               21,00
Base imponible 10%    50,00
IVA 10%                5,00
Total factura        176,00
"""


def test_importes_en_distintos_formatos():
    assert _parse_importe("1.234,56") == 1234.56
    assert _parse_importe("1,234.56") == 1234.56
    assert _parse_importe("210,00") == 210.0
    assert _parse_importe("1234.5") == 1234.5
    assert _parse_importe("-150,00") == -150.0
    assert _parse_importe("1.060") == 1060.0


def test_nif_cif_nie_validos_e_invalidos():
    assert nif_cif_valido("12345678Z")
    assert nif_cif_valido("x1234567l")
    assert nif_cif_valido("B-12345674")
    assert nif_cif_valido("ESB12345674")
    assert nif_cif_valido("A58818501")
    assert not nif_cif_valido("12345678A")
    assert not nif_cif_valido("B12345675")
    assert normalizar_nif("ES B-123.456.74") == "B12345674"


def test_factura_castellano_ingreso_con_retencion():
    r = analizar_texto(FACTURA_ES_INGRESO, USUARIO)
    assert r.numero == "F-2026-001"
    assert r.fecha == date(2026, 3, 15)
    assert r.emisor.nif == "12345678Z" and r.emisor.nombre == "Juan Pérez García"
    assert r.receptor.nif == "B12345674" and r.receptor.nombre == "Cliente Ejemplo S.L."
    assert r.base_imponible == 1000.0
    assert r.tipo_iva == 21.0
    assert r.retencion_irpf_pct == 15.0
    assert r.total == 1060.0
    assert r.tipo == "ingreso"
    assert not [a for a in r.avisos if "cuadran" in a]


def test_factura_catalan_es_un_gasto():
    r = analizar_texto(FACTURA_CA_GASTO, USUARIO)
    assert r.numero == "2026/0045"
    assert r.fecha == date(2026, 3, 3)
    assert r.emisor.nif == "A58818501" and r.emisor.nombre == "Subministraments Catalans S.A."
    assert r.receptor.nif == "12345678Z" and r.receptor.nombre == "Joan Martí Puig"
    assert (r.base_imponible, r.tipo_iva, r.total) == (200.0, 21.0, 242.0)
    assert r.retencion_irpf_pct is None
    assert r.tipo == "gasto"


def test_factura_ingles_es_un_gasto():
    r = analizar_texto(FACTURA_EN_GASTO, USUARIO)
    assert r.numero == "INV-2026-118"
    assert r.fecha == date(2026, 3, 12)
    assert r.emisor.nif == "B12345674" and r.emisor.nombre == "Acme Software Ltd"
    assert r.receptor.nif == "12345678Z" and r.receptor.nombre == "Maria Lopez"
    assert (r.base_imponible, r.tipo_iva, r.total) == (500.0, 21.0, 605.0)
    assert r.tipo == "gasto"


def test_tabla_con_cabecera_y_fila_de_valores():
    r = analizar_texto(FACTURA_TABLA, USUARIO)
    assert r.numero == "F-77"
    assert r.fecha == date(2026, 2, 1)
    assert (r.base_imponible, r.tipo_iva, r.total) == (800.0, 21.0, 968.0)
    assert r.emisor.nif == "B12345674"
    assert r.tipo == "gasto"


def test_varios_tipos_de_iva_avisa():
    r = analizar_texto(FACTURA_VARIOS_IVA, USUARIO)
    assert any("varios tipos de IVA" in a for a in r.avisos)


def test_sin_nif_del_usuario_no_clasifica():
    r = analizar_texto(FACTURA_ES_INGRESO, "99999999R")
    assert r.tipo is None
    assert any("Tu NIF/CIF no aparece" in a for a in r.avisos)


def test_total_que_no_cuadra_avisa():
    texto = FACTURA_ES_INGRESO.replace("1.060,00", "1.100,00")
    r = analizar_texto(texto, USUARIO)
    assert any("no cuadran" in a for a in r.avisos)


def test_retencion_deducida_del_total_sin_etiqueta_de_porcentaje():
    texto = """
    Factura 5
    Fecha 01/06/2026
    Estudio Gráfico SL
    CIF B12345674
    Cliente: Pedro Ruiz
    NIF 12345678Z
    Base imponible 1.000,00
    IVA 21% 210,00
    Total factura 1.060,00
    """
    r = analizar_texto(texto, USUARIO)
    assert r.retencion_irpf_pct == 15.0
    assert any("retención" in a.lower() for a in r.avisos)


def test_texto_ilegible():
    r = analizar_texto("xx", USUARIO)
    assert r.base_imponible is None
    assert r.avisos


# --- Mejoras para facturas leídas con OCR y otros formatos ---------------------------------

def test_nif_mal_leido_por_ocr_se_corrige_con_el_digito_de_control():
    from app.services.invoice_parser import _reparar_nif

    assert _reparar_nif("123456782") == "12345678Z"   # Z leída como 2
    assert _reparar_nif("123456787") == "12345678Z"   # Z leída como 7
    assert _reparar_nif("8123456O4") is None or _reparar_nif("8123456O4") == "B12345674"
    assert _reparar_nif("987654321") is None           # sin arreglo válido: no se inventa nada


def test_nif_reparado_genera_aviso():
    texto = """
    Factura 12
    Fecha 01/03/2026
    Empresa Demo SL
    CIF B12345674
    Cliente: Pedro Ruiz
    NIF: 123456782
    Base imponible 100,00
    IVA 21% 21,00
    Total 121,00
    """
    r = analizar_texto(texto, USUARIO)
    assert r.receptor.nif == "12345678Z"
    assert r.tipo == "gasto"
    assert any("se ha corregido" in a for a in r.avisos)


def test_identificador_de_otro_pais_de_la_ue():
    texto = """
    Invoice no. 2026-014
    Date: 20 March 2026
    Juan Pérez García
    Tax ID: 12345678Z
    Bill to
    Globex GmbH
    VAT No: DE123456789
    Subtotal €2,000.00
    VAT (0%) €0.00
    Total €2,000.00
    """
    r = analizar_texto(texto, USUARIO)
    assert r.receptor.nif == "DE123456789" and r.receptor.nif_valido is None
    assert r.receptor.nombre == "Globex GmbH"
    assert r.tipo == "ingreso"
    assert r.tipo_iva == 0.0 and r.base_imponible == 2000.0
    assert any("otro país" in a for a in r.avisos)


def test_numero_de_factura_en_formatos_variados():
    for texto, esperado in [
        ("FACTURA N' 2026/007\nFecha 01/01/2026", "2026/007"),
        ("Número: 260312\nData emissió: 12/03/2026", "260312"),
        ("Factura número: 2026-088", "2026-088"),
        ("Nº Fra.: 5521", "5521"),
        ("Invoice #: INV-77", "INV-77"),
    ]:
        assert analizar_texto(texto + "\nEmpresa Demo SL\nCIF B12345674\nTotal 10,00", USUARIO).numero == esperado, texto


def test_nombre_con_etiqueta_delante_en_la_misma_linea():
    texto = """
    Factura A-1
    Fecha 01/04/2026
    Inmobiliaria Sol, S.L.
    CIF B12345674
    Arrendatario: Juan Pérez García, NIF 12345678Z
    Base imponible 800,00
    IVA 21% 168,00
    Total 968,00
    """
    r = analizar_texto(texto, USUARIO)
    assert r.receptor.nombre == "Juan Pérez García"
    assert r.emisor.nombre == "Inmobiliaria Sol, S.L."


def test_importe_sin_porcentaje_legible_usa_la_cuota_para_deducir_el_iva():
    texto = """
    Factura 9
    Fecha 01/04/2026
    Empresa Demo SL
    CIF B12345674
    Cliente: Pedro Ruiz
    NIF 12345678Z
    Base imponible   900,00 €
    IVA (21 90)      189,00 €
    Total   1.089,00 €
    """
    r = analizar_texto(texto, USUARIO)
    assert r.tipo_iva == 21.0
    assert any("deducido" in a for a in r.avisos)


def test_lectura_por_columnas_separa_emisor_y_cliente():
    from app.services.ocr import _columnas

    def seg(x0, x1, t):
        return (x0, x1, t)

    filas = [
        [seg(50, 300, "Maquinaria Industrial S.L."), seg(500, 700, "Cliente")],
        [seg(50, 300, "Polígono La Palma"), seg(500, 700, "Juan Pérez García")],
        [seg(50, 300, "41007 Sevilla"), seg(500, 700, "NIF 12345678Z")],
        [seg(50, 300, "CIF: Q2826000H")],
    ]
    texto = _columnas(filas, ancho=800, altura=20)
    assert texto.split("\n") == [
        "Maquinaria Industrial S.L.", "Polígono La Palma", "41007 Sevilla", "CIF: Q2826000H",
        "Cliente", "Juan Pérez García", "NIF 12345678Z",
    ]
    assert _columnas([[seg(50, 300, "Solo una columna")]] * 4, ancho=800, altura=20) == ""


def test_tipo_de_archivo_se_detecta_por_el_contenido():
    import pytest

    from app.services.ocr import ErrorLectura, tipo_de_archivo

    assert tipo_de_archivo(b"%PDF-1.7 ...") == "pdf"
    assert tipo_de_archivo(b"\x89PNG\r\n\x1a\n") == "imagen"
    assert tipo_de_archivo(b"\xff\xd8\xff\xe0") == "imagen"
    with pytest.raises(ErrorLectura) as e:
        tipo_de_archivo(b"MZ ejecutable")
    assert e.value.estado == 415
