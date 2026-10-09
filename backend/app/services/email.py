"""
Envío de correo transaccional con Resend.

Sin RESEND_API_KEY configurada, no se envía nada (se registra en el log): así el
registro de usuarios sigue funcionando en local sin tener que dar de alta cuentas.
El envío nunca lanza una excepción hacia quien lo llama — un fallo de Resend no debe
impedir que el registro se complete.
"""

import logging

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)

_configurado = False


def _asegurar_configurado() -> bool:
    global _configurado
    if not settings.RESEND_API_KEY:
        return False
    if not _configurado:
        resend.api_key = settings.RESEND_API_KEY
        _configurado = True
    return True


def enviar_correo_verificacion(destinatario: str, nombre: str | None, enlace: str) -> bool:
    """Devuelve True si se envió (o se intentó enviar sin error), False si no hay nada configurado."""
    if not _asegurar_configurado():
        logger.warning("RESEND_API_KEY no configurada: no se envía el correo de verificación a %s", destinatario)
        return False

    saludo = f"Hola {nombre}," if nombre else "Hola,"
    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
      <h2>Confirma tu correo</h2>
      <p>{saludo}</p>
      <p>Gracias por registrarte en Finanzas Autónomo. Confirma tu correo para activar tu cuenta:</p>
      <p>
        <a href="{enlace}" style="background:#4f46e5;color:#fff;padding:10px 18px;border-radius:8px;
           text-decoration:none;display:inline-block;">Confirmar mi correo</a>
      </p>
      <p style="color:#6b7280;font-size:13px;">
        Si el botón no funciona, copia este enlace en tu navegador:<br>{enlace}
      </p>
      <p style="color:#6b7280;font-size:13px;">El enlace caduca en 48 horas.</p>
    </div>
    """
    try:
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": destinatario,
            "subject": "Confirma tu correo · Finanzas Autónomo",
            "html": html,
        })
        return True
    except Exception:
        logger.exception("No se ha podido enviar el correo de verificación a %s", destinatario)
        return False
