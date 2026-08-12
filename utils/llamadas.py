# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Auto-respuesta por SMS a llamadas entrantes mientras se graba una
reunión. Android no permite que una app normal conteste la llamada ni
reproduzca un mensaje de voz (eso exige ser la app de teléfono
predeterminada del sistema, con permisos que Google restringe mucho) --
lo que sí es viable sin eso es detectar el timbrado vía el broadcast del
sistema PHONE_STATE y enviar un SMS automático al número que llama. El
teléfono sigue timbrando normalmente."""
from kivy.utils import platform

_receiver = None
_ultimo_estado = None
_numero_actual = None
_intentos_sms = 0
_evento_reintento = None
_mensaje_actual = ''

MAX_INTENTOS_SMS = 3
INTERVALO_REINTENTO_SMS = 5  # segundos entre reintentos mientras siga timbrando


def _log(mensaje):
    """Registro de depuración temporal (ver [[project_agenda_build_android]]):
    todo lo demás en este módulo se traga las excepciones para no romper la
    grabación si algo de esto falla, así que sin esto es imposible saber por
    qué no llegó un SMS. Escribe en app_storage_path()/llamadas_debug.log."""
    try:
        import traceback
        from datetime import datetime
        from android.storage import app_storage_path
        import os
        ruta = os.path.join(app_storage_path(), 'llamadas_debug.log')
        with open(ruta, 'a', encoding='utf-8') as f:
            f.write(f'[{datetime.now().isoformat()}] {mensaje}\n')
    except Exception:
        pass


def iniciar(mensaje):
    """Empieza a escuchar llamadas entrantes. No hace nada fuera de Android."""
    global _mensaje_actual
    _mensaje_actual = mensaje
    if platform != 'android':
        return
    _log(f'iniciar() llamado, mensaje={mensaje!r}')
    from android.permissions import check_permission, request_permissions, Permission
    permisos = [Permission.READ_PHONE_STATE, Permission.READ_CALL_LOG, Permission.SEND_SMS]
    estado_permisos = {p: check_permission(p) for p in permisos}
    _log(f'permisos actuales: {estado_permisos}')
    if all(estado_permisos.values()):
        _iniciar_receiver()
        return

    def _en_respuesta(_permissions, resultados):
        _log(f'respuesta de request_permissions: {list(zip(_permissions, resultados))}')
        if resultados and all(resultados):
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: _iniciar_receiver(), 0)

    request_permissions(permisos, _en_respuesta)


def detener():
    global _receiver, _ultimo_estado, _numero_actual, _intentos_sms
    if platform != 'android' or _receiver is None:
        return
    _log('detener()')
    _cancelar_reintento()
    try:
        _receiver.stop()
    except Exception as e:
        _log(f'excepción al detener receiver: {e!r}')
    _receiver = None
    _ultimo_estado = None
    _numero_actual = None
    _intentos_sms = 0


def _iniciar_receiver():
    global _receiver, _ultimo_estado, _numero_actual, _intentos_sms
    if _receiver is not None:
        _log('_iniciar_receiver: ya había uno activo, se ignora')
        return
    try:
        from android.broadcast import BroadcastReceiver
        _ultimo_estado = None
        _numero_actual = None
        _intentos_sms = 0
        _receiver = BroadcastReceiver(_on_broadcast, actions=['android.intent.action.PHONE_STATE'])
        _receiver.start()
        _log('_iniciar_receiver: receiver registrado OK')
    except Exception as e:
        import traceback
        _log(f'_iniciar_receiver: EXCEPCIÓN al registrar receiver: {e!r}\n{traceback.format_exc()}')
        raise


def _on_broadcast(_context, intent):
    global _ultimo_estado, _numero_actual, _intentos_sms
    estado = intent.getStringExtra('state')
    numero = intent.getStringExtra('incoming_number')
    _log(f'_on_broadcast: estado={estado!r} numero={numero!r} (anterior={_ultimo_estado!r})')
    # El timbrado dispara VARIOS broadcasts en RINGING seguidos -- el primero
    # normalmente sin el número (llega en uno posterior) -- así que no alcanza
    # con comparar contra el estado anterior para no repetir el ciclo. Se usa
    # _numero_actual (no una bandera booleana) para poder cancelar los
    # reintintos si el estado cambia (llamada contestada/colgada) antes de
    # agotar MAX_INTENTOS_SMS.
    if estado == 'RINGING':
        if numero and _numero_actual is None:
            _numero_actual = numero
            _intentos_sms = 0
            _enviar_sms_con_reintento()
    else:
        _cancelar_reintento()
        _numero_actual = None
        _intentos_sms = 0
    _ultimo_estado = estado


def _cancelar_reintento():
    global _evento_reintento
    if _evento_reintento is not None:
        _evento_reintento.cancel()
        _evento_reintento = None


def _enviar_sms_con_reintento(_dt=None):
    """sendTextMessage() no confirma que el SMS realmente salió (ver
    [[project_agenda]]) -- para que el mensaje llegue de todas formas, se
    reenvía hasta MAX_INTENTOS_SMS veces cada INTERVALO_REINTENTO_SMS
    segundos mientras la llamada siga timbrando. Se cancela apenas cambia
    el estado (contestada/colgada) en _on_broadcast, así que no sigue
    reenviando después de que la llamada ya terminó."""
    global _intentos_sms, _evento_reintento
    if _numero_actual is None:
        return
    _enviar_sms(_numero_actual)
    _intentos_sms += 1
    if _intentos_sms < MAX_INTENTOS_SMS:
        from kivy.clock import Clock
        _evento_reintento = Clock.schedule_once(_enviar_sms_con_reintento, INTERVALO_REINTENTO_SMS)


def _enviar_sms(numero):
    _log(f'_enviar_sms: intentando enviar a {numero!r} (intento {_intentos_sms + 1}/{MAX_INTENTOS_SMS})')
    try:
        from jnius import autoclass
        SmsManager = autoclass('android.telephony.SmsManager')
        SmsManager.getDefault().sendTextMessage(numero, None, _mensaje_actual, None, None)
        _log('_enviar_sms: sendTextMessage OK (sin excepción)')
    except Exception as e:
        import traceback
        _log(f'_enviar_sms: EXCEPCIÓN: {e!r}\n{traceback.format_exc()}')
