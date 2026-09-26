"""
Extracción de campos de una factura a partir de su texto (castellano, catalán, inglés).

Es un analizador por reglas: no entiende el documento, busca etiquetas y patrones
habituales. Por eso devuelve siempre avisos y el resultado debe revisarse antes de
guardarlo. No accede a la base de datos ni a ficheros: recibe texto y devuelve datos.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from app.services.nif import nif_cif_valido, normalizar_nif

TIPOS_IVA_HABITUALES = (0.0, 2.0, 4.0, 5.0, 7.0, 10.0, 21.0)
RETENCIONES_HABITUALES = (1.0, 2.0, 7.0, 15.0, 19.0, 21.0)
TOLERANCIA_EUROS = 0.05


@dataclass
class Parte:
    nif: Optional[str] = None
    nombre: Optional[str] = None
    nif_valido: Optional[bool] = None


@dataclass
class ResultadoFactura:
    numero: Optional[str] = None
    fecha: Optional[date] = None
    emisor: Parte = field(default_factory=Parte)
    receptor: Parte = field(default_factory=Parte)
    base_imponible: Optional[float] = None
    tipo_iva: Optional[float] = None
    retencion_irpf_pct: Optional[float] = None
    total: Optional[float] = None
    tipo: Optional[str] = None  # "ingreso" | "gasto" | None si no se puede saber
    avisos: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------

def _plano_char(c: str) -> str:
    """Minúscula sin acento, siempre de longitud 1 para mantener los índices alineados."""
    base = "".join(ch for ch in unicodedata.normalize("NFD", c) if not unicodedata.combining(ch))
    return (base[:1] or c).lower()


def _plano(linea: str) -> str:
    return "".join(_plano_char(c) for c in linea)


def _lineas(texto: str) -> list[str]:
    texto = texto.replace("\r", "\n").replace(" ", " ").replace("\t", "  ")
    lineas = [re.sub(r"[ ]{3,}", "   ", l).strip() for l in texto.split("\n")]
    return [l for l in lineas if l]


# ---------------------------------------------------------------------------
# Importes
# ---------------------------------------------------------------------------

_NUM = r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:[.,]\d{1,2})?"
_IMPORTE = re.compile(rf"(?<![\d.,])([-−–]?\s?(?:{_NUM}))(?![\d])")


def _parse_importe(txt: str) -> Optional[float]:
    t = txt.strip().replace("−", "-").replace("–", "-").replace(" ", "")
    negativo = t.startswith("-")
    t = t.lstrip("-")
    if not t:
        return None
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".") if len(t.split(",")[-1]) <= 2 else t.replace(",", "")
    elif "." in t:
        trozos = t.split(".")
        if len(trozos[-1]) == 3 and len(trozos[0]) <= 3:
            t = t.replace(".", "")
    try:
        valor = float(t)
    except ValueError:
        return None
    return -valor if negativo else valor


def _importes_en(linea: str, desde: int = 0, solo_decimales: bool = False) -> list[float]:
    """Importes de una línea desde una posición, sin contar porcentajes."""
    encontrados = []
    for m in _IMPORTE.finditer(linea, desde):
        resto = linea[m.end():m.end() + 3].lstrip()
        if resto.startswith("%"):
            continue
        if solo_decimales and not re.search(r"[.,]\d{1,2}$", m.group(1)):
            continue
        valor = _parse_importe(m.group(1))
        if valor is not None:
            encontrados.append(valor)
    return encontrados


def _porcentaje(txt: str) -> float:
    return float(txt.replace(",", "."))


# ---------------------------------------------------------------------------
# Fecha
# ---------------------------------------------------------------------------

MESES = {
    "enero": 1, "gener": 1, "january": 1, "jan": 1, "ene": 1, "gen": 1,
    "febrero": 2, "febrer": 2, "february": 2, "feb": 2,
    "marzo": 3, "marc": 3, "march": 3, "mar": 3,
    "abril": 4, "april": 4, "apr": 4, "abr": 4,
    "mayo": 5, "maig": 5, "may": 5,
    "junio": 6, "juny": 6, "june": 6, "jun": 6,
    "julio": 7, "juliol": 7, "july": 7, "jul": 7,
    "agosto": 8, "agost": 8, "august": 8, "aug": 8, "ago": 8,
    "septiembre": 9, "setiembre": 9, "setembre": 9, "september": 9, "sep": 9, "sept": 9, "set": 9,
    "octubre": 10, "october": 10, "oct": 10,
    "noviembre": 11, "novembre": 11, "november": 11, "nov": 11,
    "diciembre": 12, "desembre": 12, "december": 12, "dec": 12, "dic": 12,
}

_FECHA_NUM = re.compile(r"(?<![\d.,])(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4}|\d{2})(?![\d])")
_FECHA_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_FECHA_TXT_DMY = re.compile(r"(?<!\d)(\d{1,2})(?:st|nd|rd|th)?\s*(?:de|d')?\s*([a-z]{3,10})\.?,?\s*(?:de|del)?\s*(\d{4})")
_FECHA_TXT_MDY = re.compile(r"\b([a-z]{3,10})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})")

_ETIQUETA_FECHA_EMISION = ("fecha factura", "fecha de factura", "fecha emision", "fecha de emision",
                           "fecha expedicion", "fecha de expedicion", "data factura", "data de factura",
                           "data emissio", "data d'emissio", "invoice date", "issue date", "date of issue",
                           "fecha de la factura", "data de la factura")
_ETIQUETA_FECHA_GENERICA = ("fecha", "data", "date")
_ETIQUETA_NO_EMISION = ("vencimiento", "vto", "venciment", "due", "pago", "pagament", "payment", "servicio",
                        "prestacion", "periodo", "period")


def _crear_fecha(d: int, m: int, a: int) -> Optional[date]:
    if a < 100:
        a += 2000
    if not 2000 <= a <= 2100:
        return None
    try:
        return date(a, m, d)
    except ValueError:
        return None


def _fechas_en(plana: str) -> list[date]:
    encontradas: list[date] = []
    for m in _FECHA_ISO.finditer(plana):
        f = _crear_fecha(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        if f:
            encontradas.append(f)
    for m in _FECHA_NUM.finditer(plana):
        f = _crear_fecha(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if f:
            encontradas.append(f)
    for m in _FECHA_TXT_DMY.finditer(plana):
        mes = MESES.get(m.group(2))
        f = _crear_fecha(int(m.group(1)), mes, int(m.group(3))) if mes else None
        if f:
            encontradas.append(f)
    for m in _FECHA_TXT_MDY.finditer(plana):
        mes = MESES.get(m.group(1))
        f = _crear_fecha(int(m.group(2)), mes, int(m.group(3))) if mes else None
        if f:
            encontradas.append(f)
    return encontradas


def _extraer_fecha(planas: list[str]) -> Optional[date]:
    mejor: tuple[int, int, date] | None = None  # (puntuación, -posición, fecha)
    for i, plana in enumerate(planas):
        # Solo cuenta lo que hay antes de una etiqueta de vencimiento/pago/periodo en la misma línea
        cortes = [m.start() for e in _ETIQUETA_NO_EMISION if (m := re.search(rf"\b{e}", plana))]
        zona = plana[: min(cortes)] if cortes else plana
        fechas = _fechas_en(zona)
        if not fechas:
            continue
        puntos = 0
        if any(e in zona for e in _ETIQUETA_FECHA_EMISION):
            puntos += 3
        elif any(re.search(rf"\b{e}\b", zona) for e in _ETIQUETA_FECHA_GENERICA):
            puntos += 1
        candidato = (puntos, -i, fechas[0])
        if mejor is None or candidato[:2] > mejor[:2]:
            mejor = candidato
    return mejor[2] if mejor else None


# ---------------------------------------------------------------------------
# Número de factura
# ---------------------------------------------------------------------------

_TOKEN = r"([a-z0-9][a-z0-9\-/._]{0,24})"
# Se aplican sobre el texto "plano" (minúsculas, sin acentos), que conserva las posiciones del original.
_N = r"n[º°o'’´ª]"  # "Nº" tal cual o como lo suele leer el OCR (N', N°, No...)
_NUMERO_PATRONES = [
    re.compile(rf"(?:factura|invoice|fra\.?)\s*(?:{_N}\.?|num(?:ero|\.)?|no\.?|number|#)\s*[:.\-]?\s*{_TOKEN}"),
    re.compile(rf"(?:{_N}\.?|num(?:ero|\.)?)\s*(?:de\s+)?(?:factura|fra\.?)\s*[:.\-]?\s*{_TOKEN}"),
    re.compile(rf"invoice\s*(?:no\.?|number|#)?\s*[:.\-]?\s*{_TOKEN}"),
    re.compile(rf"(?:factura|invoice)\s*[:\-]\s*{_TOKEN}"),
    re.compile(rf"\b(?:factura|invoice)\s+{_TOKEN}"),
    re.compile(rf"(?:^|\s)(?:n[º°'’´ªp]\.?|num\.?|#)\s*[:.\-]?\s*{_TOKEN}"),  # "Nº F-2026-0031" suelto
    re.compile(rf"\bnumero\s*[:.\-]\s*{_TOKEN}"),  # "Número: 260312" sin la palabra factura
]
_PALABRAS_NO_NUMERO = {"de", "del", "fecha", "date", "data", "para", "to", "from", "no", "num", "numero",
                       "electronica", "proforma", "simplificada", "rectificativa", "n", "total"}


def _extraer_numero(lineas: list[str], planas: list[str]) -> Optional[str]:
    for patron in _NUMERO_PATRONES:
        for i, plana in enumerate(planas[:250]):
            m = patron.search(plana)
            if not m:
                continue
            token = lineas[i][m.start(1):m.end(1)].rstrip(".-/:")
            if token.lower() in _PALABRAS_NO_NUMERO or not re.search(r"\d", token):
                continue
            if _fechas_en(_plano(token)):  # parece una fecha, no un número
                continue
            return token
    return None


# ---------------------------------------------------------------------------
# Identificación fiscal (NIF / CIF / NIE)
# ---------------------------------------------------------------------------

_NIF_RE = re.compile(
    r"(?<![A-Z0-9ÁÉÍÓÚÑÜ])(?:ES[\s\-]?)?"
    r"(?:\d{2}[.\s]?\d{3}[.\s]?\d{3}[\s\-]?[A-Z]"
    r"|[XYZ][\s\-.]?\d{7}[\s\-.]?[A-Z]"
    r"|[A-HJ-NP-SUVW][\s\-.]?\d{7}[\s\-.]?[0-9A-J])"
    r"(?![A-Z0-9ÁÉÍÓÚÑÜ])"
)
_ETIQUETA_NIF = re.compile(r"\b(nif|cif|nie|dni|vat|tax\s*id|n\.i\.f|c\.i\.f|id\s*fiscal)\b")

_KW_RECEPTOR = ("facturar a", "facturat a", "factura a", "bill to", "billed to", "invoice to", "sold to",
                "cliente", "client", "customer", "destinatario", "destinatari", "receptor", "comprador",
                "pagador", "arrendatario", "titular", "adquirente")
_KW_EMISOR = ("emisor", "emissor", "proveedor", "proveidor", "vendedor", "venedor", "expedidor", "seller",
              "supplier", "issued by", "prestador", "acreedor", "profesional", "arrendador", "from:", "de:")
_RELLENO_ENCABEZADO = r"\b(datos|dades|del|de|la|el|los|les|d'|l'|servicio|servei|fiscales|fiscals)\b"

LETRA_A_DIGITO = {"O": "0", "I": "1", "L": "1", "S": "5", "B": "8", "Z": "2", "G": "6"}
DIGITO_A_LETRA = {"2": "Z", "7": "Z", "5": "S", "8": "B", "6": "G", "4": "A"}

# Identificador fiscal europeo de otro país tras una etiqueta VAT / Tax ID (p. ej. DE123456789)
_VAT_EXTRANJERO = re.compile(r"(?:VAT|TAX\s*ID|USTID|UST|TVA|BTW)[^A-Z0-9]{0,12}(?:(?:NO|NR|ID|NUMBER)\.?[^A-Z0-9]{0,6})?([A-Z]{2}[A-Z0-9]{8,12})\b")


@dataclass
class _NifHit:
    nif: str
    valido: Optional[bool]  # None = identificador extranjero que no se puede comprobar
    linea: int
    rol: Optional[str] = None  # "emisor" | "receptor" | None
    leido: Optional[str] = None  # texto original si se corrigió un error típico de OCR


def _reparar_nif(c: str) -> Optional[str]:
    """
    Corrige confusiones típicas de OCR (Z↔2, B↔8, S↔5, O↔0...) en un identificador de 9 caracteres.
    Solo se acepta la variante que supera el dígito de control.
    """
    if len(c) != 9:
        return None
    hipotesis = (
        ("D" * 8 + "L"),  # DNI: 8 dígitos y letra
        ("L" + "D" * 7 + "C"),  # CIF: letra, 7 dígitos y control (letra o dígito)
        ("L" + "D" * 7 + "L"),  # NIE: letra, 7 dígitos y letra
    )
    for forma in hipotesis:
        candidato = []
        for ch, tipo in zip(c, forma):
            if tipo == "D":
                candidato.append(LETRA_A_DIGITO.get(ch, ch))
            elif tipo == "L":
                candidato.append(DIGITO_A_LETRA.get(ch, ch))
            else:
                candidato.append(ch)
        nif = "".join(candidato)
        if nif_cif_valido(nif):
            return nif
    return None


def _buscar_nifs(lineas: list[str], planas: list[str]) -> list[_NifHit]:
    hits: list[_NifHit] = []
    vistos: set[str] = set()
    for i, linea in enumerate(lineas):
        etiqueta = _ETIQUETA_NIF.search(planas[i])
        encontrado_en_linea = False
        for m in _NIF_RE.finditer(linea.upper()):
            nif = normalizar_nif(m.group(0))
            valido = nif_cif_valido(nif)
            if not valido and not etiqueta:
                continue
            encontrado_en_linea = True
            if nif in vistos:
                continue
            vistos.add(nif)
            hits.append(_NifHit(nif=nif, valido=valido, linea=i))

        if etiqueta and not encontrado_en_linea:  # posible NIF mal leído por el OCR
            resto = re.sub(r"[\s.\-]", "", linea[etiqueta.end():].upper())
            resto = re.sub(r"^[^A-Z0-9]+", "", resto)
            m = re.match(r"(?:ES)?([A-Z0-9]{9})", resto)
            if m:
                arreglado = _reparar_nif(m.group(1))
                if arreglado and arreglado not in vistos:
                    vistos.add(arreglado)
                    hits.append(_NifHit(nif=arreglado, valido=True, linea=i, leido=m.group(1)))
                    encontrado_en_linea = True

        if etiqueta and not encontrado_en_linea:  # identificador de otro país de la UE
            m = _VAT_EXTRANJERO.search(linea.upper())
            if m and not m.group(1).startswith("ES") and m.group(1) not in vistos:
                vistos.add(m.group(1))
                hits.append(_NifHit(nif=m.group(1), valido=None, linea=i))
    return hits


def _rol_por_contexto(hit: _NifHit, planas: list[str]) -> Optional[str]:
    contexto = "\n".join(planas[max(0, hit.linea - 3): hit.linea + 1])
    ultimo = {"emisor": -1, "receptor": -1}
    for rol, kws in (("emisor", _KW_EMISOR), ("receptor", _KW_RECEPTOR)):
        for kw in kws:
            # La palabra debe terminar ahí: "factura a" no puede ser el "Factura A-1" de un número de factura
            patron = rf"\b{re.escape(kw)}" + ("" if kw.endswith(":") else r"(?![\w\-])")
            for m in re.finditer(patron, contexto):
                ultimo[rol] = max(ultimo[rol], m.start())
    if ultimo["emisor"] < 0 and ultimo["receptor"] < 0:
        return None
    return "emisor" if ultimo["emisor"] > ultimo["receptor"] else "receptor"


_SUFIJOS_SOCIEDAD = re.compile(
    r"\b(s\.?\s?l\.?\s?u?\.?|s\.?\s?a\.?\s?u?\.?|s\.?\s?c\.?\s?p\.?|c\.?\s?b\.?|s\.?\s?coop\.?|s\.?\s?l\.?\s?l\.?|"
    r"ltd\.?|limited|inc\.?|llc|gmbh|sarl|s\.?r\.?l\.?|b\.?v\.?)(?=[\s,.]|$)", re.I)
_NO_NOMBRE = re.compile(
    r"\b(factura|invoice|fecha|data|date|total|base|iva|vat|irpf|nif|cif|dni|nie|tel|tlf|telefono|movil|mobile|"
    r"email|e-mail|correo|web|www|iban|swift|banco|bank|vencimiento|concepto|descripcion|cantidad|precio|"
    r"importe|amount|forma de pago|pago|cliente|client|customer|proveedor|emisor|destinatario|datos|dades|"
    r"facturar|facturat|bill|registro mercantil|inscrit|inscrita)\b", re.I)
_DIRECCION = re.compile(
    r"\b(calle|c/|carrer|avda|avenida|av\.|plaza|pl\.|passeig|paseo|pº|camino|ronda|travesia|urbanizacion|"
    r"street|st\.|road|rd\.|avenue|ave\.|nave|poligono|pol\.|edificio|piso|planta|c\.p\.|cp)\b|\b\d{5}\b", re.I)
_ETIQUETAS_NOMBRE = {
    "emisor": r"emisor|emissor|proveedor|proveidor|vendedor|venedor|seller|supplier|arrendador|profesional",
    "receptor": r"cliente|client|customer|destinatario|destinatari|comprador|pagador|arrendatario|titular",
    "neutro": r"razon social|nombre|nom|empresa|company|name",
}
_CORTE_NOMBRE = re.compile(r"\s+[—–·|\-]*\s*(?:nif|cif|vat|tel|tlf|email|e-mail|dni)\b.*$", re.I)
_LIMPIAR_NOMBRE = " :-,—–·|"


def _puntuar_nombre(linea: str, plana: str) -> int:
    if len(linea) < 3 or len(linea) > 70:
        return -100
    if "@" in linea or "http" in plana or "www." in plana:
        return -100
    if _NIF_RE.search(linea.upper()):
        return -50
    letras = sum(c.isalpha() for c in linea)
    digitos = sum(c.isdigit() for c in linea)
    if letras < 3 or digitos > letras:
        return -100
    puntos = 0
    con_sufijo = bool(_SUFIJOS_SOCIEDAD.search(linea))
    if con_sufijo:
        puntos += 4
    if _NO_NOMBRE.search(plana):
        puntos -= 1 if con_sufijo else 5
    if _DIRECCION.search(plana):
        puntos -= 5
    if linea.isupper() or linea.istitle():
        puntos += 1
    if len(linea.split()) >= 2:
        puntos += 1
    return puntos


def _nombre_cerca(hit: _NifHit, lineas: list[str], planas: list[str], rol: str) -> Optional[str]:
    # 1) Nombre etiquetado ("Cliente: ...", "Proveedor: ..."): primero en la propia línea, luego en las cercanas.
    #    Solo cuentan las etiquetas de ese rol o neutras, para no dar al cliente el nombre del proveedor.
    etiqueta = re.compile(rf"(?:{_ETIQUETAS_NOMBRE[rol]}|{_ETIQUETAS_NOMBRE['neutro']})\s*[:\-]\s*(.+)", re.I)
    cercanas = sorted(range(max(0, hit.linea - 3), min(len(lineas), hit.linea + 3)), key=lambda i: abs(i - hit.linea))
    for i in cercanas:
        m = etiqueta.search(_plano(lineas[i]))
        if m:
            valor = lineas[i][m.start(1):m.end(1)]
            valor = _CORTE_NOMBRE.sub("", valor).strip(_LIMPIAR_NOMBRE)
            if valor and not _NIF_RE.search(valor.upper()) and _puntuar_nombre(valor, _plano(valor)) > -50:
                return valor

    # 2) La línea más parecida a un nombre cerca del NIF. Hacia arriba sin cruzar la cabecera del bloque
    #    ("Facturar a:", "Emisor"...) ni otro NIF; luego un par de líneas hacia abajo.
    ventana = [hit.linea]
    inicio_bloque = None
    for i in range(hit.linea - 1, max(-1, hit.linea - 6), -1):
        if _es_encabezado(planas[i]):
            inicio_bloque = ventana[-1]
            break
        if _NIF_RE.search(lineas[i].upper()):
            break
        ventana.append(i)
    else:
        if ventana[-1] == 0:  # el bloque empieza en la primera línea del documento
            inicio_bloque = 0
    for i in range(hit.linea + 1, min(len(lineas), hit.linea + 3)):
        if _es_encabezado(planas[i]) or _NIF_RE.search(lineas[i].upper()):
            break
        ventana.append(i)

    mejor: tuple[float, str] | None = None
    for distancia, i in enumerate(ventana):
        texto = lineas[i]
        if i == hit.linea:  # nombre en la misma línea, antes de "NIF:"
            antes = _ETIQUETA_NIF.split(planas[i])[0]
            texto = lineas[i][: len(antes)]
        texto = _CORTE_NOMBRE.sub("", texto).strip(_LIMPIAR_NOMBRE)
        texto = re.sub(r"^[^:\d]{1,25}:\s*", "", texto).strip(_LIMPIAR_NOMBRE)  # "Arrendatario: Nombre" -> "Nombre"
        puntos = _puntuar_nombre(texto, _plano(texto))
        if puntos <= -50:
            continue
        if i == inicio_bloque and i != hit.linea:
            puntos += 2  # la primera línea de un bloque suele ser el nombre
        puntos -= distancia / 2
        if puntos > 0 and (mejor is None or puntos > mejor[0]):
            mejor = (puntos, texto)
    return mejor[1] if mejor else None


def _es_encabezado(plana: str) -> bool:
    """Línea corta que solo introduce un bloque: "Emisor", "Facturar a:", "Datos del cliente"..."""
    if len(plana) > 40 or re.search(r"\d", plana):
        return False
    resto = plana
    for kw in sorted(_KW_EMISOR + _KW_RECEPTOR, key=len, reverse=True):
        resto = re.sub(rf"\b{re.escape(kw.rstrip(':'))}\b", "", resto)
    coincidio = resto != plana
    resto = re.sub(_RELLENO_ENCABEZADO, "", resto)
    return coincidio and len(re.sub(r"[^a-z]", "", resto)) <= 3


def _asignar_partes(lineas, planas, nif_usuario: Optional[str], avisos: list) -> tuple[Parte, Parte, Optional[str]]:
    hits = _buscar_nifs(lineas, planas)
    for h in hits:
        h.rol = _rol_por_contexto(h, planas)

    emisor_hit = next((h for h in hits if h.rol == "emisor"), None)
    receptor_hit = next((h for h in hits if h.rol == "receptor" and h is not emisor_hit), None)
    restantes = [h for h in hits if h is not emisor_hit and h is not receptor_hit]

    if emisor_hit is None and restantes:
        emisor_hit = restantes.pop(0)
    if receptor_hit is None and restantes:
        receptor_hit = restantes.pop(0)

    emisor, receptor = Parte(), Parte()
    for parte, hit, rol in ((emisor, emisor_hit, "emisor"), (receptor, receptor_hit, "receptor")):
        if hit:
            parte.nif = hit.nif
            parte.nif_valido = hit.valido
            parte.nombre = _nombre_cerca(hit, lineas, planas, rol)
            if hit.leido:
                avisos.append(f"El NIF/CIF del {rol} se leyó como {hit.leido} y se ha corregido a {hit.nif}: compruébalo.")
    if emisor_hit is None:
        avisos.append("No se ha encontrado el NIF/CIF del emisor.")
    if receptor_hit is None:
        avisos.append("No se ha encontrado el NIF/CIF del cliente o pagador.")
    for etiqueta, parte in (("emisor", emisor), ("cliente o pagador", receptor)):
        if parte.nif and parte.nif_valido is False:
            avisos.append(f"El NIF/CIF del {etiqueta} ({parte.nif}) no supera el dígito de control: revísalo.")
        elif parte.nif and parte.nif_valido is None:
            avisos.append(f"El identificador fiscal del {etiqueta} ({parte.nif}) es de otro país y no se puede comprobar.")

    tipo = None
    if nif_usuario:
        mio = normalizar_nif(nif_usuario)
        if emisor.nif == mio:
            tipo = "ingreso"
        elif receptor.nif == mio:
            tipo = "gasto"
    return emisor, receptor, tipo


# ---------------------------------------------------------------------------
# Importes: base, IVA, IRPF y total
# ---------------------------------------------------------------------------

_LINEA_IRPF = re.compile(r"irpf|retencion|retencio|retention|withholding|\bret\.")
_IVA_PCT = re.compile(r"(?:\biva\b|i\.v\.a|\bvat\b|\bigic\b|\btva\b)[^\d%\n]{0,25}(\d{1,2}(?:[.,]\d{1,2})?)\s*%")
_IVA_PCT_INV = re.compile(r"(\d{1,2}(?:[.,]\d{1,2})?)\s*%\s*(?:de\s+)?(?:iva|vat|igic)\b")
_IRPF_PCT = re.compile(
    r"(?:irpf|retencion(?:es)?(?:\s+de)?(?:\s+irpf)?|retencio(?:\s+irpf)?|retention|withholding(?:\s+tax)?|\bret\.?)"
    r"[^\d%\n]{0,20}[-−–]?\s*(\d{1,2}(?:[.,]\d{1,2})?)\s*%")
_IRPF_PCT_INV = re.compile(r"(\d{1,2}(?:[.,]\d{1,2})?)\s*%\s*(?:de\s+)?(?:irpf|retencion|retencio|retention)")

_BASE_FUERTE = re.compile(
    r"base\s+imponible|base\s+imposable|importe\s+base|base\s+iva|total\s+base|base\s+impuestos?|"
    r"taxable\s+(?:amount|base|value)|net\s+(?:amount|total|value)|import\s+net|importe\s+neto|total\s+neto|"
    r"total\s+sin\s+iva|total\s+antes\s+de\s+impuestos|amount\s+before\s+tax")
_BASE_SUBTOTAL = re.compile(r"sub-?\s?total")
_TOTAL_FUERTE = re.compile(
    r"total\s+factura|total\s+a\s+pagar|total\s+a\s+abonar|total\s+a\s+ingresar|importe\s+total|total\s+importe|"
    r"import\s+total|total\s+invoice|invoice\s+total|amount\s+due|total\s+due|total\s+eur|total\s+€|"
    r"total\s+a\s+liquidar|total\s+factura\s*\(?iva")
_TOTAL_DEBIL = re.compile(r"\btotal\b")
_TOTAL_EXCLUIR = re.compile(r"total\s+(?:base|iva|impuestos?|vat|tax|cuota|descuentos?|retenci)|subtotal|sub-total|"
                            r"base\s+imponible|total\s+neto|total\s+sin")


def _primer_importe(planas: list[str], lineas: list[str], patron: re.Pattern, tras_etiqueta: bool = True) -> list[float]:
    """Importes que aparecen tras una etiqueta (misma línea o, si no hay, la siguiente)."""
    misma_linea, siguiente = [], []
    for i, plana in enumerate(planas):
        m = patron.search(plana)
        if not m:
            continue
        importes = _importes_en(lineas[i], m.end())
        if importes:
            misma_linea.append(importes[0])
        elif i + 1 < len(lineas):
            en_siguiente = _importes_en(lineas[i + 1])[:1]
            if en_siguiente:
                siguiente.append(en_siguiente[0])
    return misma_linea or siguiente


def _extraer_importes(lineas: list[str], planas: list[str], avisos: list) -> dict:
    res: dict = {"base": None, "iva": None, "irpf": None, "total": None, "cuota_iva": None, "irpf_importe": None}

    # Tipos de IVA (líneas que no son de IRPF)
    tipos_iva: list[float] = []
    cuotas_iva: list[float] = []
    for i, plana in enumerate(planas):
        for patron in (_IVA_PCT, _IVA_PCT_INV):
            for m in patron.finditer(plana):
                if _LINEA_IRPF.search(plana[max(0, m.start() - 12): m.start() + 1]):
                    continue
                pct = _porcentaje(m.group(1))
                if 0 <= pct <= 30:
                    tipos_iva.append(pct)
                    importes = _importes_en(lineas[i], m.end())
                    if importes:
                        cuotas_iva.append(importes[-1])
    distintos = sorted(set(tipos_iva))
    varios_iva = len(distintos) > 1
    if distintos:
        res["iva"] = tipos_iva[0]
        res["cuota_iva"] = cuotas_iva[0] if cuotas_iva else None
        if varios_iva:
            avisos.append(
                "La factura tiene varios tipos de IVA (" + ", ".join(f"{d:g}%" for d in distintos) +
                "). Cada documento admite uno solo: introduce la base y el IVA a mano o regístrala en varios documentos."
            )
    res["varios_iva"] = varios_iva
    if not tipos_iva:  # porcentaje ilegible (p. ej. "IVA (21 90)"): se usa la cuota para deducirlo
        for i, plana in enumerate(planas):
            m = re.search(r"\b(?:iva|vat|igic)\b", plana)
            if m and not _LINEA_IRPF.search(plana):
                importes = _importes_en(lineas[i], m.end(), solo_decimales=True)
                if importes:
                    res["cuota_iva"] = importes[-1]
                    break

    # IRPF
    for i, plana in enumerate(planas):
        for patron in (_IRPF_PCT, _IRPF_PCT_INV):
            m = patron.search(plana)
            if m and res["irpf"] is None:
                res["irpf"] = _porcentaje(m.group(1))
                importes = _importes_en(lineas[i], m.end())
                if importes:
                    res["irpf_importe"] = abs(importes[-1])
    if res["irpf"] is None:
        for i, plana in enumerate(planas):
            m = re.search(r"(?:irpf|retencion|retencio|retention|withholding)[^\d\n]{0,25}", plana)
            if m:
                importes = _importes_en(lineas[i], m.end(), solo_decimales=True)
                if importes:
                    res["irpf_importe"] = abs(importes[-1])
                    break

    # Base imponible
    bases = _primer_importe(planas, lineas, _BASE_FUERTE)
    if not bases:
        bases = _primer_importe(planas, lineas, _BASE_SUBTOTAL)
    if bases:
        res["base"] = bases[0]
        if len({round(b, 2) for b in bases}) > 1 and len(distintos) > 1:
            res["base"] = bases[0]

    # Total: el último importe con etiqueta de total (el total general suele ir al final)
    # (fuerte/débil, misma línea/siguiente) -> importes; se prefiere lo más fiable que exista
    candidatos: dict[tuple[bool, bool], list[float]] = {(f, m): [] for f in (True, False) for m in (True, False)}
    for i, plana in enumerate(planas):
        if _TOTAL_EXCLUIR.search(plana):
            continue
        for fuerte, patron in ((True, _TOTAL_FUERTE), (False, _TOTAL_DEBIL)):
            m = patron.search(plana)
            if m:
                importes = _importes_en(lineas[i], m.end())
                if importes:
                    candidatos[(fuerte, True)].append(importes[-1])
                elif i + 1 < len(lineas):
                    en_siguiente = _importes_en(lineas[i + 1])[:1]
                    if en_siguiente:
                        candidatos[(fuerte, False)].append(en_siguiente[0])
                break
    for clave in ((True, True), (False, True), (True, False), (False, False)):
        if candidatos[clave]:
            res["total"] = candidatos[clave][-1]
            break

    # Tabla de resumen con cabecera y fila de valores (Base | % IVA | Cuota | Total)
    for i, plana in enumerate(planas[:-1]):
        if re.search(r"\bbase\b", plana) and re.search(r"\b(iva|vat|cuota|quota)\b", plana) and not _importes_en(lineas[i]):
            importes = _importes_en(lineas[i + 1])
            if len(importes) < 2:
                continue
            if res["base"] is None:
                res["base"] = importes[0]
            if res["cuota_iva"] is None and len(importes) >= 3 and re.search(r"cuota|quota", plana):
                res["cuota_iva"] = importes[-2]
            if res["total"] is None and re.search(r"\btotal\b", plana):
                res["total"] = importes[-1]
            if res["iva"] is None:
                m = re.search(r"(\d{1,2}(?:[.,]\d{1,2})?)\s*%", planas[i + 1])
                if m:
                    res["iva"] = _porcentaje(m.group(1))
            break
    return res


def _mas_cercano(valor: float, habituales: tuple, tolerancia: float) -> Optional[float]:
    mejor = min(habituales, key=lambda h: abs(h - valor))
    return mejor if abs(mejor - valor) <= tolerancia else None


def _cuadrar(res: dict, avisos: list) -> tuple:
    if res.get("varios_iva"):  # ambiguo: se deja en blanco para que se rellene a mano
        return None, None, res["irpf"], res["total"]

    base, iva, irpf, total = res["base"], res["iva"], res["irpf"], res["total"]
    cuota, irpf_imp = res["cuota_iva"], res["irpf_importe"]

    if irpf is None and irpf_imp and base:
        cercano = _mas_cercano(irpf_imp / base * 100, RETENCIONES_HABITUALES, 0.3)
        if cercano is not None:
            irpf = cercano
            avisos.append(f"IRPF deducido del importe de la retención ({cercano:g}%): compruébalo.")

    if iva is None and base and cuota is not None:
        cercano = _mas_cercano(cuota / base * 100, TIPOS_IVA_HABITUALES, 0.5)
        if cercano is not None:
            iva = cercano
            avisos.append(f"Tipo de IVA deducido de la cuota ({cercano:g}%): compruébalo.")

    if iva is None and base and total:
        efectivo = (total - base) / base * 100 + (irpf or 0)
        cercano = _mas_cercano(efectivo, TIPOS_IVA_HABITUALES, 0.6)
        if cercano is not None:
            iva = cercano
            avisos.append(f"Tipo de IVA deducido de la base y el total ({cercano:g}%): compruébalo.")

    if base is None and total and iva is not None:
        base = round(total / (1 + iva / 100 - (irpf or 0) / 100), 2)
        avisos.append("La base imponible se ha calculado a partir del total: compruébala.")
    elif base is None and cuota and iva:
        base = round(cuota * 100 / iva, 2)
        avisos.append("La base imponible se ha calculado a partir de la cuota de IVA: compruébala.")

    if irpf is None and base and total and iva is not None:
        esperado_sin_irpf = base * (1 + iva / 100)
        if total < esperado_sin_irpf - TOLERANCIA_EUROS:
            cercano = _mas_cercano((esperado_sin_irpf - total) / base * 100, RETENCIONES_HABITUALES, 0.3)
            if cercano is not None:
                irpf = cercano
                avisos.append(f"El total sugiere una retención de IRPF del {cercano:g}%: compruébalo.")

    if base is not None and iva is not None and total is not None:
        esperado = base * (1 + iva / 100 - (irpf or 0) / 100)
        if abs(esperado - total) > max(TOLERANCIA_EUROS, total * 0.001):
            avisos.append(
                f"Los importes no cuadran: base {base:.2f} + IVA {iva:g}% "
                f"{'− IRPF ' + format(irpf, 'g') + '% ' if irpf else ''}= {esperado:.2f}, pero el total leído es {total:.2f}."
            )
    return base, iva, irpf, total


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def analizar_texto(texto: str, nif_usuario: Optional[str] = None) -> ResultadoFactura:
    lineas = _lineas(texto)
    planas = [_plano(l) for l in lineas]
    avisos: list[str] = []

    if len("".join(lineas)) < 30:
        return ResultadoFactura(avisos=["No se ha podido leer texto en el documento."])

    numero = _extraer_numero(lineas, planas)
    fecha = _extraer_fecha(planas)
    emisor, receptor, tipo = _asignar_partes(lineas, planas, nif_usuario, avisos)
    importes = _extraer_importes(lineas, planas, avisos)
    base, iva, irpf, total = _cuadrar(importes, avisos)

    if numero is None:
        avisos.append("No se ha encontrado el número de factura.")
    if fecha is None:
        avisos.append("No se ha encontrado la fecha.")
    if base is None:
        avisos.append("No se ha encontrado la base imponible.")
    if iva is None:
        avisos.append("No se ha encontrado el tipo de IVA.")
    if nif_usuario and tipo is None and (emisor.nif or receptor.nif):
        avisos.append("Tu NIF/CIF no aparece en la factura, así que no se puede saber si es un ingreso o un gasto.")

    return ResultadoFactura(
        numero=numero, fecha=fecha, emisor=emisor, receptor=receptor,
        base_imponible=base, tipo_iva=iva, retencion_irpf_pct=irpf, total=total,
        tipo=tipo, avisos=avisos,
    )
