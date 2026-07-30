# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Selector nativo de Android para elegir un archivo cualquiera para adjuntar.

Se evita plyer.filechooser por el mismo motivo que en foto_selector.py: en
Android devuelve URIs content:// que no se pueden copiar con shutil.copy2
directamente (no son rutas de archivo reales). Aqui se usa un Intent nativo
mas ContentResolver -- mismo patron que utils/foto_selector.py."""
import os
from kivy.clock import Clock

_REQUEST_CODE_ARCHIVO = 1004


def abrir_selector(dest_dir, on_seleccionado, on_error=None):
    """Abre el selector de archivos de Android (Intent.ACTION_GET_CONTENT,
    tipo */*). Llama on_seleccionado(ruta_local, nombre_original) con una
    copia local del archivo elegido, o on_error(mensaje) si algo falla. Si
    el usuario cancela, no llama a ninguno de los dos."""
    try:
        from jnius import autoclass
        from android import activity

        Intent = autoclass('android.content.Intent')
        Activity = autoclass('android.app.Activity')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')

        intent = Intent(Intent.ACTION_GET_CONTENT)
        intent.setType('*/*')
        intent.addCategory(Intent.CATEGORY_OPENABLE)

        def _on_activity_result(request_code, result_code, data):
            if request_code != _REQUEST_CODE_ARCHIVO:
                return
            activity.unbind(on_activity_result=_on_activity_result)
            if result_code != Activity.RESULT_OK or data is None:
                return
            uri = data.getData()
            if uri is None:
                if on_error:
                    Clock.schedule_once(lambda dt: on_error(
                        'No se pudo obtener el archivo seleccionado.'), 0)
                return
            try:
                nombre = _obtener_nombre(uri)
                ruta = _copiar_uri_a_archivo(uri, dest_dir, nombre)
            except Exception as e:
                mensaje = f'No se pudo leer el archivo: {e}'
                if on_error:
                    Clock.schedule_once(lambda dt: on_error(mensaje), 0)
                return
            Clock.schedule_once(lambda dt: on_seleccionado(ruta, nombre), 0)

        activity.bind(on_activity_result=_on_activity_result)
        PythonActivity.mActivity.startActivityForResult(intent, _REQUEST_CODE_ARCHIVO)
    except Exception as e:
        if on_error:
            on_error(f'Error al abrir el selector de archivos: {e}')


def _obtener_nombre(uri):
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    OpenableColumns = autoclass('android.provider.OpenableColumns')

    resolver = PythonActivity.mActivity.getContentResolver()
    cursor = resolver.query(uri, None, None, None, None)
    nombre = None
    if cursor is not None:
        try:
            if cursor.moveToFirst():
                idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if idx >= 0:
                    nombre = cursor.getString(idx)
        finally:
            cursor.close()
    return nombre or 'archivo_adjunto'


def _copiar_uri_a_archivo(uri, dest_dir, nombre):
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    FileOutputStream = autoclass('java.io.FileOutputStream')

    resolver = PythonActivity.mActivity.getContentResolver()
    entrada = resolver.openInputStream(uri)
    os.makedirs(dest_dir, exist_ok=True)
    ruta = os.path.join(dest_dir, nombre)
    salida = FileOutputStream(ruta)
    try:
        buf = bytearray(65536)
        while True:
            n = entrada.read(buf)
            if n == -1:
                break
            salida.write(buf, 0, n)
    finally:
        salida.close()
        entrada.close()
    return ruta
