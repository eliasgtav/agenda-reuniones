# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Silencia el timbre de llamadas entrantes (y el resto de notificaciones)
mientras se graba una reunión, y restaura todo al terminar. Android exige
el permiso especial "Acceso a No Molestar" para poder tocar el volumen/modo
del timbre desde una app (desde Android 7), no hay forma de silenciarlo sin
ese permiso.

Usa RINGER_MODE_SILENT (silencio total, sin vibrar) en vez de solo bajar
el volumen del stream RING a 0 -- se probó esto último primero, pero
Android convierte volumen-0 en modo vibrador automáticamente, y el motor
de vibración se colaba como zumbido en la grabación. RINGER_MODE_SILENT sí
frena la vibración, a costa de silenciar también otras notificaciones
(WhatsApp, etc.) mientras se graba -- decisión explícita del usuario, que
prefiere silencio total a que la vibración se escuche en la grabación.

El volumen y modo previos se guardan en el config en disco (no en una
variable en memoria): si la app se cierra/crashea mientras está
silenciado, quedaría mudo para siempre sin esto -- restaurar() se llama de
nuevo en el próximo arranque (main.py::on_start) y sí puede recuperarlo."""
from kivy.utils import platform


def _log(mensaje):
    """Registro de depuración temporal, mismo patrón que utils/llamadas.py
    (ver [[project_agenda_build_android]]) -- los prints de Python no
    aparecen con ningún tag reconocible en logcat en este dispositivo, y
    todo lo demás en este módulo se traga las excepciones en silencio."""
    try:
        from datetime import datetime
        from android.storage import app_storage_path
        import os
        ruta = os.path.join(app_storage_path(), 'llamadas_debug.log')
        with open(ruta, 'a', encoding='utf-8') as f:
            f.write(f'[{datetime.now().isoformat()}] [silenciador] {mensaje}\n')
    except Exception:
        pass


def _audio_manager():
    from jnius import autoclass
    Context = autoclass('android.content.Context')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    activity = PythonActivity.mActivity
    return activity.getSystemService(Context.AUDIO_SERVICE), autoclass('android.media.AudioManager')


def tiene_permiso():
    if platform != 'android':
        return False
    try:
        from jnius import autoclass
        Context = autoclass('android.content.Context')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        nm = activity.getSystemService(Context.NOTIFICATION_SERVICE)
        resultado = bool(nm.isNotificationPolicyAccessGranted())
        _log(f'tiene_permiso() -> {resultado}')
        return resultado
    except Exception as e:
        _log(f'tiene_permiso(): EXCEPCIÓN: {e!r}')
        return False


def pedir_permiso():
    """Abre la pantalla de Configuración de Android donde el usuario concede
    el acceso a No Molestar. No hay diálogo in-app posible para esto."""
    if platform != 'android':
        return
    try:
        from jnius import autoclass
        Settings = autoclass('android.provider.Settings')
        Intent = autoclass('android.content.Intent')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        intent = Intent(Settings.ACTION_NOTIFICATION_POLICY_ACCESS_SETTINGS)
        activity.startActivity(intent)
    except Exception:
        pass


def silenciar():
    """Guarda el modo de timbre y volumen actuales en el config y pone el
    teléfono en RINGER_MODE_SILENT (sin sonido ni vibración). No hace nada
    si falta el permiso (la llamada seguirá timbrando normal, sin romper el
    resto de la grabación)."""
    if platform != 'android' or not tiene_permiso():
        _log('silenciar(): sin permiso o no es Android, se ignora')
        return
    try:
        from utils.config import cargar, guardar
        audio, AudioManager = _audio_manager()
        config = cargar()
        modo_actual = audio.getRingerMode()
        volumen_actual = audio.getStreamVolume(AudioManager.STREAM_RING)
        config['_ring_modo_respaldo'] = modo_actual
        config['_ring_volumen_respaldo'] = volumen_actual
        guardar(config)
        audio.setRingerMode(AudioManager.RINGER_MODE_SILENT)
        _log(f'silenciar(): OK, modo anterior={modo_actual} volumen anterior={volumen_actual}')
    except Exception as e:
        import traceback
        _log(f'silenciar(): EXCEPCIÓN: {e!r}\n{traceback.format_exc()}')


def restaurar():
    """Devuelve el timbre al modo y volumen que tenía antes de grabar (si
    había quedado algo guardado)."""
    if platform != 'android':
        return
    try:
        from utils.config import cargar, guardar
        config = cargar()
        modo = config.pop('_ring_modo_respaldo', None)
        volumen = config.pop('_ring_volumen_respaldo', None)
        if modo is None and volumen is None:
            return
        guardar(config)
        audio, AudioManager = _audio_manager()
        if modo is not None:
            audio.setRingerMode(modo)
        if volumen is not None:
            audio.setStreamVolume(AudioManager.STREAM_RING, volumen, 0)
        _log(f'restaurar(): OK, modo restaurado={modo} volumen restaurado={volumen}')
    except Exception as e:
        import traceback
        _log(f'restaurar(): EXCEPCIÓN: {e!r}\n{traceback.format_exc()}')
