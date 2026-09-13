# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from utils.notas_acuerdos import separar as separar_notas_acuerdos

_MENSAJE_ERROR_AUTENTICACION = (
    'Error de autenticación Gmail.\n\n'
    'Pasos para solucionarlo:\n'
    '1. Ve a myaccount.google.com\n'
    '2. Seguridad → Verificación en 2 pasos (actívala)\n'
    '3. Seguridad → Contraseñas de aplicación\n'
    '4. Crea una para "Agenda de Reuniones"\n'
    '5. Usa esa contraseña (16 caracteres) en el campo "Contraseña de '
    'aplicación" del Perfil'
)


def _enviar_smtp(smtp_server, smtp_port, origen, password, destino, msg):
    # Intenta STARTTLS (puerto 587), luego SSL (puerto 465)
    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(origen, password)
            server.sendmail(origen, destino, msg.as_string())
    except smtplib.SMTPAuthenticationError:
        raise
    except Exception:
        with smtplib.SMTP_SSL(smtp_server, 465, timeout=15) as server:
            server.login(origen, password)
            server.sendmail(origen, destino, msg.as_string())


def _enviar_correo_async(config, asunto, cuerpo, mensaje_incompleto, mensaje_exito, callback=None):
    """Arma un correo simple (From/To/Subject + cuerpo de texto plano) y lo
    manda en un hilo aparte -- logica compartida entre probar_conexion() y
    enviar_acta(), que antes la duplicaban casi entera (extraccion de
    credenciales, validacion, armado de MIMEMultipart, manejo de
    excepciones). La duplicacion ya habia divergido: enviar_acta atrapaba
    ConnectionRefusedError con un mensaje especifico y probar_conexion no,
    asi que esa falla exacta -- justo la que probar_conexion existe para
    detectar -- caia en su mensaje generico "Error de conexión: {e}"."""
    def _enviar():
        correo_origen  = config.get('correo_origen', '').strip()
        password       = config.get('correo_password', '').strip()
        correo_destino = config.get('correo_destino', '').strip()
        smtp_server    = config.get('smtp_server', 'smtp.gmail.com').strip()
        smtp_port      = int(config.get('smtp_port', 587))

        if not correo_origen or not password or not correo_destino:
            if callback:
                callback(False, mensaje_incompleto)
            return
        try:
            msg = MIMEMultipart()
            msg['From']    = correo_origen
            msg['To']      = correo_destino
            msg['Subject'] = asunto
            msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))
            _enviar_smtp(smtp_server, smtp_port, correo_origen, password, correo_destino, msg)
            if callback:
                callback(True, mensaje_exito)
        except smtplib.SMTPAuthenticationError:
            if callback:
                callback(False, _MENSAJE_ERROR_AUTENTICACION)
        except ConnectionRefusedError:
            if callback:
                callback(False, 'No se pudo conectar al servidor SMTP.\nVerifica el servidor y el puerto.')
        except Exception as e:
            if callback:
                callback(False, f'Error de conexión: {e}')
    threading.Thread(target=_enviar, daemon=True).start()


def probar_conexion(config, callback=None):
    destino = config.get('correo_destino', '').strip()
    _enviar_correo_async(
        config,
        asunto='Prueba — Agenda de Reuniones',
        cuerpo='Conexión de correo configurada correctamente.',
        mensaje_incompleto='Completa todos los campos de correo en Perfil.',
        mensaje_exito=f'¡Correo de prueba enviado a {destino}!',
        callback=callback,
    )


def _componer_acta(reunion, participantes, acuerdos_texto=''):
    linea = '=' * 50
    fecha_envio = datetime.now().strftime('%d/%m/%Y %H:%M')

    partic = '\n'.join(
        f"  • {p['nombre']} — {'Asistió' if p['asistio'] else 'No asistió'}"
        for p in participantes
    ) or '  (Sin participantes registrados)'

    notas_raw, bloque_acuerdos = separar_notas_acuerdos(reunion.get('notas', ''))
    notas = notas_raw or '(Sin notas)'
    conclusion = reunion.get('conclusion', '').strip() or '(Sin conclusión registrada)'
    acuerdos = bloque_acuerdos or (acuerdos_texto.strip() if acuerdos_texto else '')

    cuerpo = f"""
{linea}
        ACTA DE REUNIÓN DE TRABAJO
{linea}

ASUNTO  : {reunion['asunto']}
FECHA   : {reunion['fecha']}
HORA    : {reunion['hora']}
LUGAR   : {reunion.get('lugar') or 'No especificado'}
ESTADO  : {reunion['estado'].upper()}

{linea}
PARTICIPANTES
{linea}
{partic}

{linea}
TEMAS TRATADOS / NOTAS
{linea}
{notas}
"""

    if acuerdos:
        cuerpo += f"""
{linea}
ACUERDOS REGISTRADOS
{linea}
{acuerdos}
"""

    cuerpo += f"""
{linea}
CONCLUSIÓN
{linea}
{conclusion}

{linea}
Acta generada el {fecha_envio}
Agenda de Reuniones de Trabajo
© Elías Gaytan Alvino
{linea}
"""
    return cuerpo


def enviar_acta(reunion, participantes, config, callback=None):
    destino = config.get('correo_destino', '').strip()
    _enviar_correo_async(
        config,
        asunto=f"Acta de Reunión: {reunion['asunto']} — {reunion['fecha']}",
        cuerpo=_componer_acta(reunion, participantes),
        mensaje_incompleto='Configura el correo en la pantalla de Perfil.',
        mensaje_exito=f'Acta enviada correctamente a:\n{destino}',
        callback=callback,
    )
