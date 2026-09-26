"""Validación del dígito de control de NIF, NIE y CIF españoles."""

import re

LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"
LETRAS_CONTROL_CIF = "JABCDEFGHI"
CIF_CONTROL_LETRA = "PQRSNW"
CIF_CONTROL_DIGITO = "ABEH"

_DNI = re.compile(r"^(\d{8})([A-Z])$")
_NIE = re.compile(r"^([XYZ])(\d{7})([A-Z])$")
_CIF = re.compile(r"^([ABCDEFGHJKLMNPQRSUVW])(\d{7})([0-9A-J])$")


def normalizar_nif(valor: str) -> str:
    """Mayúsculas, sin espacios, guiones ni puntos y sin el prefijo de país ES."""
    v = re.sub(r"[\s.\-]", "", valor.upper())
    if len(v) == 11 and v.startswith("ES"):
        v = v[2:]
    return v


def _dni_valido(v: str) -> bool:
    m = _DNI.match(v)
    return bool(m) and LETRAS_DNI[int(m.group(1)) % 23] == m.group(2)


def _nie_valido(v: str) -> bool:
    m = _NIE.match(v)
    if not m:
        return False
    numero = str("XYZ".index(m.group(1))) + m.group(2)
    return LETRAS_DNI[int(numero) % 23] == m.group(3)


def _cif_valido(v: str) -> bool:
    m = _CIF.match(v)
    if not m:
        return False
    tipo, digitos, control = m.groups()
    suma = 0
    for i, c in enumerate(digitos):
        d = int(c)
        if i % 2 == 0:
            doble = d * 2
            suma += doble - 9 if doble > 9 else doble
        else:
            suma += d
    digito = (10 - suma % 10) % 10
    letra = LETRAS_CONTROL_CIF[digito]

    if tipo in CIF_CONTROL_LETRA or tipo in "KLM":
        return control == letra
    if tipo in CIF_CONTROL_DIGITO:
        return control == str(digito)
    return control in (str(digito), letra)


def nif_cif_valido(valor: str) -> bool:
    v = normalizar_nif(valor)
    return _dni_valido(v) or _nie_valido(v) or _cif_valido(v)
