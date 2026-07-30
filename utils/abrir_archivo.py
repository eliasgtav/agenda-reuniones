# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Abre un archivo adjunto con la app externa que el sistema elija (visor de
PDF, imagenes, etc.), para poder confirmar que se adjunto bien.

En Android, un archivo dentro del almacenamiento privado de la app
(getFilesDir(), ver utils/foto_selector.py/archivo_selector.py) no puede
compartirse directo con otra app via file:// desde Android 7 -- lanza
FileUriExposedException. Se usa androidx.core.content.FileProvider (Uri
content:// temporal con permiso de lectura), declarado en el manifest via
buildozer.spec (android.extra_manifest_application_arguments +
android.add_resources -- ver src/android/extra_manifest_application_arguments.xml
y android_res/xml/file_paths.xml)."""
import mimetypes
from kivy.utils import platform


def abrir(ruta, nombre, on_error=None):
    if platform == 'android':
        _abrir_android(ruta, nombre, on_error)
    else:
        _abrir_desktop(ruta, on_error)


def _abrir_desktop(ruta, on_error):
    import os
    import subprocess
    import sys
    try:
        if sys.platform == 'win32':
            os.startfile(ruta)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', ruta])
        else:
            subprocess.Popen(['xdg-open', ruta])
    except Exception as e:
        if on_error:
            on_error(f'No se pudo abrir el archivo: {e}')


def _abrir_android(ruta, nombre, on_error):
    try:
        from jnius import autoclass

        Intent = autoclass('android.content.Intent')
        FileProvider = autoclass('androidx.core.content.FileProvider')
        File = autoclass('java.io.File')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')

        activity = PythonActivity.mActivity
        authority = activity.getPackageName() + '.fileprovider'
        uri = FileProvider.getUriForFile(activity, authority, File(ruta))

        mime = mimetypes.guess_type(nombre)[0] or '*/*'

        intent = Intent(Intent.ACTION_VIEW)
        intent.setDataAndType(uri, mime)
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

        if intent.resolveActivity(activity.getPackageManager()) is None:
            if on_error:
                on_error('No hay una aplicación instalada que pueda abrir este archivo.')
            return

        activity.startActivity(intent)
    except Exception as e:
        if on_error:
            on_error(f'No se pudo abrir el archivo: {e}')
