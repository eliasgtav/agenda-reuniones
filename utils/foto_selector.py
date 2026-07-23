# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Selectores nativos de Android para elegir o tomar una foto de perfil.

Se evita plyer.filechooser: en Android devuelve URIs content:// que PIL no
puede abrir directamente, y en pruebas reales en dispositivo el selector no
llegaba a mostrar/cargar la imagen. Aqui se usa un Intent nativo mas
ContentResolver/Bitmap -- mismo patron ya probado y funcionando en
utils/contactos.py (selector de contactos)."""
import os
from kivy.clock import Clock

_REQUEST_CODE_GALERIA = 1002
_REQUEST_CODE_CAMARA = 1003


def abrir_galeria(dest_dir, on_seleccionado, on_error=None):
    """Abre el selector de imagenes de Android (Intent.ACTION_GET_CONTENT).
    Llama on_seleccionado(ruta_local) con una copia local de la imagen
    elegida, o on_error(mensaje) si algo falla. Si el usuario cancela, no
    llama a ninguno de los dos."""
    try:
        from jnius import autoclass
        from android import activity

        Intent = autoclass('android.content.Intent')
        Activity = autoclass('android.app.Activity')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')

        intent = Intent(Intent.ACTION_GET_CONTENT)
        intent.setType('image/*')
        intent.addCategory(Intent.CATEGORY_OPENABLE)

        def _on_activity_result(request_code, result_code, data):
            if request_code != _REQUEST_CODE_GALERIA:
                return
            activity.unbind(on_activity_result=_on_activity_result)
            if result_code != Activity.RESULT_OK or data is None:
                return
            uri = data.getData()
            if uri is None:
                if on_error:
                    Clock.schedule_once(lambda dt: on_error(
                        'No se pudo obtener la imagen seleccionada.'), 0)
                return
            try:
                ruta = _copiar_uri_a_archivo(uri, dest_dir, 'seleccion_galeria')
            except Exception as e:
                mensaje = f'No se pudo leer la imagen: {e}'
                if on_error:
                    Clock.schedule_once(lambda dt: on_error(mensaje), 0)
                return
            Clock.schedule_once(lambda dt: on_seleccionado(ruta), 0)

        activity.bind(on_activity_result=_on_activity_result)
        PythonActivity.mActivity.startActivityForResult(intent, _REQUEST_CODE_GALERIA)
    except Exception as e:
        if on_error:
            on_error(f'Error al abrir la galería: {e}')


def abrir_camara(dest_dir, on_seleccionado, on_error=None):
    """Pide permiso de camara si hace falta y abre la app de camara de
    Android (Intent.ACTION_IMAGE_CAPTURE, usa la miniatura de los extras --
    sin FileProvider). Llama on_seleccionado(ruta_local) o
    on_error(mensaje)."""
    from android.permissions import check_permission, request_permissions, Permission
    if check_permission(Permission.CAMERA):
        _lanzar_camara(dest_dir, on_seleccionado, on_error)
        return

    def _en_respuesta(permissions, resultados):
        if resultados and all(resultados):
            Clock.schedule_once(
                lambda dt: _lanzar_camara(dest_dir, on_seleccionado, on_error), 0
            )
        elif on_error:
            Clock.schedule_once(lambda dt: on_error(
                'Se necesita permiso de cámara. Actívalo en Ajustes del '
                'sistema > Apps > Agenda de Reuniones > Permisos > Cámara.',
            ), 0)

    request_permissions([Permission.CAMERA], _en_respuesta)


def _lanzar_camara(dest_dir, on_seleccionado, on_error):
    try:
        from jnius import autoclass
        from android import activity

        Intent = autoclass('android.content.Intent')
        MediaStore = autoclass('android.provider.MediaStore')
        Activity = autoclass('android.app.Activity')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')

        intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
        if intent.resolveActivity(PythonActivity.mActivity.getPackageManager()) is None:
            if on_error:
                on_error('No se encontró una aplicación de cámara.')
            return

        def _on_activity_result(request_code, result_code, data):
            if request_code != _REQUEST_CODE_CAMARA:
                return
            activity.unbind(on_activity_result=_on_activity_result)
            if result_code != Activity.RESULT_OK or data is None:
                return
            try:
                from jnius import cast
                extras = data.getExtras()
                bitmap = extras.getParcelable('data') if extras else None
                if bitmap is None:
                    raise ValueError('la cámara no devolvió una imagen')
                bitmap = cast('android.graphics.Bitmap', bitmap)
                ruta = _guardar_bitmap(bitmap, dest_dir, 'seleccion_camara')
            except Exception as e:
                mensaje = f'No se pudo guardar la foto: {e}'
                if on_error:
                    Clock.schedule_once(lambda dt: on_error(mensaje), 0)
                return
            Clock.schedule_once(lambda dt: on_seleccionado(ruta), 0)

        activity.bind(on_activity_result=_on_activity_result)
        PythonActivity.mActivity.startActivityForResult(intent, _REQUEST_CODE_CAMARA)
    except Exception as e:
        if on_error:
            on_error(f'Error al abrir la cámara: {e}')


def _copiar_uri_a_archivo(uri, dest_dir, nombre_base):
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    FileOutputStream = autoclass('java.io.FileOutputStream')

    resolver = PythonActivity.mActivity.getContentResolver()
    entrada = resolver.openInputStream(uri)
    os.makedirs(dest_dir, exist_ok=True)
    ruta = os.path.join(dest_dir, f'_{nombre_base}.tmp')
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


def _guardar_bitmap(bitmap, dest_dir, nombre_base):
    from jnius import autoclass
    FileOutputStream = autoclass('java.io.FileOutputStream')
    CompressFormat = autoclass('android.graphics.Bitmap$CompressFormat')

    os.makedirs(dest_dir, exist_ok=True)
    ruta = os.path.join(dest_dir, f'_{nombre_base}.png')
    salida = FileOutputStream(ruta)
    try:
        bitmap.compress(CompressFormat.PNG, 100, salida)
    finally:
        salida.close()
    return ruta
