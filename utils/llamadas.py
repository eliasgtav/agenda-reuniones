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
_mensaje_actual = ''


def iniciar(mensaje):
    """Empieza a escuchar llamadas entrantes. No hace nada fuera de Android."""
    global _mensaje_actual
    _mensaje_actual = mensaje
    if platform != 'android':
        return
    from android.permissions import check_permission, request_permissions, Permission
    permisos = [Permission.READ_PHONE_STATE, Permission.READ_CALL_LOG, Permission.SEND_SMS]
    if all(check_permission(p) for p in permisos):
        _iniciar_receiver()
        return

    def _en_respuesta(_permissions, resultados):
        if resultados and all(resultados):
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: _iniciar_receiver(), 0)

    request_permissions(permisos, _en_respuesta)


def detener():
    global _receiver, _ultimo_estado
    if platform != 'android' or _receiver is None:
        return
    try:
        _receiver.stop()
    except Exception:
        pass
    _receiver = None
    _ultimo_estado = None


def _iniciar_receiver():
    global _receiver, _ultimo_estado
    if _receiver is not None:
        return
    from android.broadcast import BroadcastReceiver
    _ultimo_estado = None
    _receiver = BroadcastReceiver(_on_broadcast, actions=['android.intent.action.PHONE_STATE'])
    _receiver.start()


def _on_broadcast(_context, intent):
    global _ultimo_estado
    estado = intent.getStringExtra('state')
    numero = intent.getStringExtra('incoming_number')
    # Solo al pasar A "RINGING" (no en cada broadcast repetido mientras
    # sigue sonando) para no mandar el SMS varias veces por la misma llamada.
    if estado == 'RINGING' and numero and _ultimo_estado != 'RINGING':
        _enviar_sms(numero)
    _ultimo_estado = estado


def _enviar_sms(numero):
    try:
        from jnius import autoclass
        SmsManager = autoclass('android.telephony.SmsManager')
        SmsManager.getDefault().sendTextMessage(numero, None, _mensaje_actual, None, None)
    except Exception:
        pass
