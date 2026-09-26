"""
Lectura de texto de PDF e imágenes de facturas.

- PDF con texto (la mayoría de las facturas digitales): se lee la capa de texto, sin OCR.
- PDF escaneado o imagen: OCR con Tesseract en castellano, catalán e inglés.
"""

import io
import re
from typing import NamedTuple, Optional

import pypdfium2 as pdfium
import pytesseract
from PIL import Image, ImageFilter, ImageOps
from pytesseract import Output

from app.core.config import settings

MAX_BYTES = 8 * 1024 * 1024
MAX_PAGINAS = 3
MAX_PIXELES = 40_000_000
IDIOMAS_DESEADOS = ("spa", "cat", "eng")
ESCALA_PDF_ESCANEADO = 2.8  # ~200 ppp
TIMEOUT_OCR = 30
CONFIANZA_MINIMA = 60  # confianza media (0-100) de Tesseract por debajo de la cual se avisa
MIN_CARACTERES_OCR = 60  # por debajo se considera que la lectura ha fallado y se reintenta

Image.MAX_IMAGE_PIXELS = MAX_PIXELES

if settings.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


class ErrorLectura(Exception):
    """Error que se puede mostrar al usuario tal cual."""

    def __init__(self, mensaje: str, estado: int = 400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.estado = estado


class Lectura(NamedTuple):
    texto: str  # el que se analiza
    metodo: str  # "texto_pdf" | "ocr"
    visible: str  # el que se enseña al usuario
    confianza: Optional[float] = None  # media de confianza del OCR (0-100); None si no hubo OCR


def tipo_de_archivo(contenido: bytes) -> str:
    """Detecta el tipo por los primeros bytes, sin fiarse del nombre ni del content-type."""
    if contenido.startswith(b"%PDF"):
        return "pdf"
    if contenido.startswith((b"\x89PNG", b"\xff\xd8\xff", b"II*\x00", b"MM\x00*")) or (
        contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP"
    ):
        return "imagen"
    raise ErrorLectura("Formato no admitido. Sube un PDF o una imagen (JPG, PNG, WebP o TIFF).", 415)


def tesseract_disponible() -> bool:
    try:
        pytesseract.get_tesseract_version()
        return True
    except pytesseract.TesseractNotFoundError:
        return False


def _idiomas_instalados() -> str:
    try:
        instalados = set(pytesseract.get_languages(config=""))
    except pytesseract.TesseractNotFoundError:
        raise ErrorLectura(
            "Este servidor no tiene OCR instalado (Tesseract), así que no puede leer imágenes ni PDF escaneados. "
            "Los PDF con texto sí se pueden leer.",
            503,
        )
    usar = [i for i in IDIOMAS_DESEADOS if i in instalados]
    if not usar:
        raise ErrorLectura("El OCR del servidor no tiene instalados los idiomas necesarios.", 503)
    return "+".join(usar)


# ---------------------------------------------------------------------------
# Preparación de la imagen
# ---------------------------------------------------------------------------

def _umbral_otsu(imagen: Image.Image) -> int:
    hist = imagen.histogram()
    total = sum(hist)
    suma = sum(i * h for i, h in enumerate(hist))
    fondo, peso_fondo, mejor, umbral = 0.0, 0, 0.0, 128
    for i in range(256):
        peso_fondo += hist[i]
        if peso_fondo == 0:
            continue
        peso_frente = total - peso_fondo
        if peso_frente == 0:
            break
        fondo += i * hist[i]
        varianza = peso_fondo * peso_frente * (fondo / peso_fondo - (suma - fondo) / peso_frente) ** 2
        if varianza > mejor:
            mejor, umbral = varianza, i
    return umbral


def _preparar(imagen: Image.Image, agresivo: bool) -> Image.Image:
    imagen = ImageOps.exif_transpose(imagen).convert("L")
    objetivo = 2400 if agresivo else 1800  # Tesseract lee mejor con letra de cierto tamaño
    if max(imagen.size) < objetivo:
        factor = objetivo / max(imagen.size)
        imagen = imagen.resize((int(imagen.width * factor), int(imagen.height * factor)), Image.LANCZOS)
    if agresivo:
        imagen = imagen.filter(ImageFilter.MedianFilter(3))  # quita el ruido de escáner
        imagen = ImageOps.autocontrast(imagen, cutoff=2)
        umbral = _umbral_otsu(imagen)
        return imagen.point(lambda v: 255 if v > umbral else 0)
    return ImageOps.autocontrast(imagen)


def _corregir_orientacion(imagen: Image.Image) -> Image.Image:
    """Gira la imagen si Tesseract detecta que está tumbada o boca abajo."""
    try:
        osd = pytesseract.image_to_osd(imagen, output_type=Output.DICT, config="--psm 0", timeout=10)
        giro = int(osd.get("rotate", 0))
        if giro in (90, 180, 270) and float(osd.get("orientation_conf", 0)) >= 2:
            return imagen.rotate(-giro, expand=True, fillcolor=255)
    except Exception:
        pass
    return imagen


# ---------------------------------------------------------------------------
# Reconstrucción del texto a partir de las palabras y sus coordenadas
# ---------------------------------------------------------------------------

def _reconstruir(datos: dict) -> tuple[str, str, str, Optional[float]]:
    """
    Devuelve (columnas, bloques, filas, confianza media de las palabras leídas).
    - bloques: orden de lectura de Tesseract; bueno para nombres y direcciones, pero separa las
      columnas, con lo que una etiqueta puede quedar lejos de su importe.
    - filas: las palabras se agrupan por su posición vertical, así "Subtotal ... 1.380,00 €" queda
      en la misma línea aunque estén en columnas distintas (las columnas se separan con 3 espacios).
    """
    palabras = []
    for k, texto in enumerate(datos["text"]):
        texto = (texto or "").strip()
        if not texto or float(datos["conf"][k]) < 0:
            continue
        palabras.append({
            "t": texto, "conf": float(datos["conf"][k]), "x": datos["left"][k], "y": datos["top"][k], "w": datos["width"][k], "h": datos["height"][k],
            "bloque": (datos["block_num"][k], datos["par_num"][k], datos["line_num"][k]),
        })
    if not palabras:
        return "", "", "", None
    confianza = sum(p["conf"] for p in palabras) / len(palabras)

    bloques, linea, clave_anterior = [], [], None
    for p in palabras:
        if p["bloque"] != clave_anterior:
            if linea:
                bloques.append(" ".join(linea))
            if clave_anterior is not None and p["bloque"][0] != clave_anterior[0]:
                bloques.append("")
            linea, clave_anterior = [], p["bloque"]
        linea.append(p["t"])
    bloques.append(" ".join(linea))

    alturas = sorted(p["h"] for p in palabras)
    altura = max(alturas[len(alturas) // 2], 8)
    filas: list[dict] = []
    for p in sorted(palabras, key=lambda p: p["y"] + p["h"] / 2):
        cy = p["y"] + p["h"] / 2
        if filas and abs(cy - filas[-1]["cy"]) <= 0.6 * altura:
            fila = filas[-1]
            fila["palabras"].append(p)
            fila["cy"] = (fila["cy"] * (len(fila["palabras"]) - 1) + cy) / len(fila["palabras"])
        else:
            filas.append({"cy": cy, "palabras": [p]})

    filas_seg = [_segmentos(fila["palabras"], altura) for fila in filas]
    lineas = ["   ".join(seg[2] for seg in fila) for fila in filas_seg]
    ancho = max(p["x"] + p["w"] for p in palabras)
    columnas = _columnas(filas_seg, ancho, altura)
    return columnas, "\n".join(bloques), "\n".join(lineas), confianza


def _segmentos(palabras: list[dict], altura: float) -> list[tuple[float, float, str]]:
    """Trocea una fila en segmentos separados por huecos grandes: (x inicial, x final, texto)."""
    segmentos: list[list] = []
    fin = None
    for p in sorted(palabras, key=lambda p: p["x"]):
        if fin is None or p["x"] - fin > 1.8 * altura:
            segmentos.append([p["x"], p["x"] + p["w"], p["t"]])
        else:
            segmentos[-1][1] = p["x"] + p["w"]
            segmentos[-1][2] += " " + p["t"]
        fin = p["x"] + p["w"]
    return [tuple(s) for s in segmentos]


def _columnas(filas_seg: list, ancho: float, altura: float) -> str:
    """
    Si el documento tiene dos columnas (p. ej. emisor a la izquierda y cliente a la derecha), devuelve el texto
    leído columna a columna. Así cada bloque conserva junto su nombre, su NIF y su dirección en vez de quedar
    mezclado línea a línea con el del otro lado. Devuelve "" si no se detectan columnas.
    """
    inicios = sorted(seg[0] for fila in filas_seg for seg in fila[1:] if 0.3 * ancho <= seg[0] <= 0.75 * ancho)
    if not inicios:
        return ""
    tolerancia = max(0.03 * ancho, altura)
    grupos: list[list[float]] = []
    for x in inicios:
        if grupos and x - grupos[-1][-1] <= tolerancia:
            grupos[-1].append(x)
        else:
            grupos.append([x])
    mejor = max(grupos, key=len)
    if len(mejor) < 3:
        return ""
    frontera = min(mejor) - tolerancia / 2

    salida: list[str] = []
    izquierda: list[str] = []
    derecha: list[str] = []

    def volcar():
        salida.extend(izquierda)
        salida.extend(derecha)
        izquierda.clear()
        derecha.clear()

    for fila in filas_seg:
        if any(seg[0] < frontera and seg[1] > frontera + tolerancia for seg in fila):  # línea de lado a lado
            volcar()
            salida.append("   ".join(seg[2] for seg in fila))
            continue
        for seg in fila:
            (derecha if seg[0] >= frontera else izquierda).append(seg[2])
    volcar()
    return "\n".join(salida)


def _ocr_una_vez(imagen: Image.Image, idiomas: str) -> tuple[str, str, str, Optional[float]]:
    try:
        datos = pytesseract.image_to_data(
            imagen, lang=idiomas, config="--oem 1 --psm 3", output_type=Output.DICT, timeout=TIMEOUT_OCR
        )
    except RuntimeError:
        raise ErrorLectura("La lectura de la imagen ha tardado demasiado. Prueba con una imagen más pequeña.", 408)
    return _reconstruir(datos)


def _caracteres(texto: str) -> int:
    return len(re.sub(r"\s", "", texto))


def _ocr(imagen: Image.Image) -> tuple[str, str, Optional[float]]:
    """Devuelve (texto para analizar, texto para mostrar, confianza media)."""
    idiomas = _idiomas_instalados()
    columnas, bloques, filas, confianza = _ocr_una_vez(_preparar(imagen, agresivo=False), idiomas)

    if _caracteres(filas) < MIN_CARACTERES_OCR:  # lectura pobre: imagen ruidosa, torcida o girada
        segunda = _corregir_orientacion(ImageOps.exif_transpose(imagen).convert("L"))
        mejor = _ocr_una_vez(_preparar(segunda, agresivo=True), idiomas)
        if _caracteres(mejor[2]) > _caracteres(filas):
            columnas, bloques, filas, confianza = mejor

    # Las columnas van primero: para nombres y NIF se usa la primera aparición; las filas quedan para los importes
    analisis = "\n\n".join(t for t in (columnas, bloques, filas) if t).strip()
    return analisis, filas, confianza


# ---------------------------------------------------------------------------
# PDF e imágenes
# ---------------------------------------------------------------------------

def _texto_pdf(contenido: bytes) -> Lectura:
    try:
        pdf = pdfium.PdfDocument(contenido)
    except Exception:
        raise ErrorLectura("No se ha podido abrir el PDF (¿está dañado o protegido con contraseña?).", 422)

    paginas = min(len(pdf), MAX_PAGINAS)
    if paginas == 0:
        raise ErrorLectura("El PDF no tiene páginas.", 422)

    textos = [(pdf[i].get_textpage().get_text_range() or "").replace("\r\n", "\n") for i in range(paginas)]
    texto = "\n".join(textos)
    if _caracteres(texto) >= 60 * paginas:
        return Lectura(texto, "texto_pdf", texto)

    # PDF escaneado: se dibuja cada página y se pasa por OCR
    _idiomas_instalados()
    analisis, visible, confianzas = [], [], []
    for i in range(paginas):
        a, v, c = _ocr(pdf[i].render(scale=ESCALA_PDF_ESCANEADO).to_pil())
        analisis.append(a)
        visible.append(v)
        if c is not None:
            confianzas.append(c)
    media = sum(confianzas) / len(confianzas) if confianzas else None
    return Lectura("\n".join(analisis), "ocr", "\n".join(visible), media)


def leer_texto(contenido: bytes) -> Lectura:
    if len(contenido) > MAX_BYTES:
        raise ErrorLectura(f"El archivo es demasiado grande (máximo {MAX_BYTES // (1024 * 1024)} MB).", 413)

    if tipo_de_archivo(contenido) == "pdf":
        return _texto_pdf(contenido)

    try:
        imagen = Image.open(io.BytesIO(contenido))
        imagen.load()
    except Image.DecompressionBombError:
        raise ErrorLectura("La imagen es demasiado grande.", 413)
    except Exception:
        raise ErrorLectura("No se ha podido abrir la imagen.", 422)
    analisis, visible, confianza = _ocr(imagen)
    return Lectura(analisis, "ocr", visible, confianza)
