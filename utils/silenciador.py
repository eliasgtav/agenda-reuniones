# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Silencia el volumen del timbre de llamadas entrantes mientras se graba
una reunión (para que no se escuche por encima de la grabación) y lo
restaura al terminar. Solo toca el stream RING, no el modo No Molestar
completo -- el resto de notificaciones del teléfono sigue sonando normal.
Android exige el permiso especial "Acceso a No Molestar" para poder
tocar el volumen/modo del timbre desde una app (desde Android 7), no hay
forma de silenciarlo sin ese permiso.

El volumen previo se guarda en el config en disco (no en una variable en
memoria): si la app se cierra/crashea mientras está silenciado, el
volumen quedaría mudo para siempre sin esto -- restaurar() se llama de
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
    """Guarda el volumen actual del timbre en el config y lo pone en 0. No
    hace nada si falta el permiso (la llamada seguirá timbrando normal, sin
    romper el resto de la grabación)."""
    if platform != 'android' or not tiene_permiso():
        _log('silenciar(): sin permiso o no es Android, se ignora')
        return
    try:
        from utils.config import cargar, guardar
        audio, AudioManager = _audio_manager()
        config = cargar()
        volumen_actual = audio.getStreamVolume(AudioManager.STREAM_RING)
        config['_ring_volumen_respaldo'] = volumen_actual
        guardar(config)
        audio.setStreamVolume(AudioManager.STREAM_RING, 0, 0)
        _log(f'silenciar(): OK, volumen anterior guardado={volumen_actual}')
    except Exception as e:
        import traceback
        _log(f'silenciar(): EXCEPCIÓN: {e!r}\n{traceback.format_exc()}')


def restaurar():
    """Devuelve el timbre al volumen que tenía antes de grabar (si había
    quedado uno guardado)."""
    if platform != 'android':
        return
    try:
        from utils.config import cargar, guardar
        config = cargar()
        volumen = config.pop('_ring_volumen_respaldo', None)
        if volumen is None:
            return
        guardar(config)
        audio, AudioManager = _audio_manager()
        audio.setStreamVolume(AudioManager.STREAM_RING, volumen, 0)
        _log(f'restaurar(): OK, volumen restaurado={volumen}')
    except Exception as e:
        import traceback
        _log(f'restaurar(): EXCEPCIÓN: {e!r}\n{traceback.format_exc()}')
