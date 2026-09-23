const LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE";
const LETRAS_CONTROL_CIF = "JABCDEFGHI";
const CIF_CONTROL_LETRA = "PQRSNW";
const CIF_CONTROL_DIGITO = "ABEH";

const normalizar = (valor) => valor.toUpperCase().replace(/[\s-]/g, "");

function esDniValido(v) {
  const m = /^(\d{8})([A-Z])$/.exec(v);
  return !!m && LETRAS_DNI[parseInt(m[1], 10) % 23] === m[2];
}

function esNieValido(v) {
  const m = /^([XYZ])(\d{7})([A-Z])$/.exec(v);
  if (!m) return false;
  const numero = "XYZ".indexOf(m[1]) + m[2];
  return LETRAS_DNI[parseInt(numero, 10) % 23] === m[3];
}

function esCifValido(v) {
  const m = /^([ABCDEFGHJKLMNPQRSUVW])(\d{7})([0-9A-J])$/.exec(v);
  if (!m) return false;
  const [, tipo, digitos, control] = m;

  let suma = 0;
  digitos.split("").forEach((c, i) => {
    const d = parseInt(c, 10);
    if (i % 2 === 0) {
      const doble = d * 2;
      suma += doble > 9 ? doble - 9 : doble;
    } else {
      suma += d;
    }
  });
  const digitoControl = (10 - (suma % 10)) % 10;
  const letraControl = LETRAS_CONTROL_CIF[digitoControl];

  if (CIF_CONTROL_LETRA.includes(tipo) || "KLM".includes(tipo)) return control === letraControl;
  if (CIF_CONTROL_DIGITO.includes(tipo)) return control === String(digitoControl);
  return control === String(digitoControl) || control === letraControl;
}

export function esNifCifValido(valor) {
  const v = normalizar(valor);
  return esDniValido(v) || esNieValido(v) || esCifValido(v);
}

export function nifAviso(valor) {
  if (!valor || !valor.trim()) return null;
  if (esNifCifValido(valor)) return null;
  return "No parece un NIF/CIF/NIE válido. Revisa que no haya errores; si es un identificador extranjero, puedes ignorar este aviso.";
}
