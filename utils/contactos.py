# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Selector de contactos nativo de Android (Intent.ACTION_PICK)."""
from kivy.utils import platform
from kivy.clock import Clock

_REQUEST_CODE = 1001


def abrir_selector(on_seleccionado, on_error=None):
    """Abre el selector de contactos de Android. Llama on_seleccionado(nombre)
    con el nombre del contacto elegido, o on_error(mensaje) si algo falla.
    Si el usuario cancela el selector, no llama a ninguno de los dos."""
    if platform != 'android':
        if on_error:
            on_error('El selector de contactos solo está disponible en Android.')
        return

    from android.permissions import check_permission, request_permissions, Permission

    if check_permission(Permission.READ_CONTACTS):
        _lanzar(on_seleccionado, on_error)
        return

    def _en_respuesta(permissions, resultados):
        if resultados and all(resultados):
            Clock.schedule_once(lambda dt: _lanzar(on_seleccionado, on_error), 0)
        elif on_error:
            Clock.schedule_once(lambda dt: on_error(
                'Se necesita permiso de contactos. Actívalo en Ajustes del '
                'sistema > Apps > Agenda de Reuniones > Permisos > Contactos.'
            ), 0)

    request_permissions([Permission.READ_CONTACTS], _en_respuesta)


def _lanzar(on_seleccionado, on_error):
    try:
        from jnius import autoclass
        from android import activity

        Intent = autoclass('android.content.Intent')
        Activity = autoclass('android.app.Activity')
        Contacts = autoclass('android.provider.ContactsContract$Contacts')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')

        intent = Intent(Intent.ACTION_PICK, Contacts.CONTENT_URI)

        def _on_activity_result(request_code, result_code, data):
            if request_code != _REQUEST_CODE:
                return
            activity.unbind(on_activity_result=_on_activity_result)
            if result_code != Activity.RESULT_OK or data is None:
                return
            nombre = _leer_nombre(data.getData())
            if nombre:
                Clock.schedule_once(lambda dt: on_seleccionado(nombre), 0)
            elif on_error:
                Clock.schedule_once(lambda dt: on_error(
                    'No se pudo leer el contacto seleccionado.'
                ), 0)

        activity.bind(on_activity_result=_on_activity_result)
        PythonActivity.mActivity.startActivityForResult(intent, _REQUEST_CODE)
    except Exception as e:
        if on_error:
            on_error(f'Error al abrir contactos: {e}')


def _leer_nombre(uri):
    from jnius import autoclass
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Contacts = autoclass('android.provider.ContactsContract$Contacts')
    resolver = PythonActivity.mActivity.getContentResolver()
    cursor = resolver.query(uri, None, None, None, None)
    nombre = None
    try:
        if cursor is not None and cursor.moveToFirst():
            idx = cursor.getColumnIndex(Contacts.DISPLAY_NAME)
            if idx >= 0:
                nombre = cursor.getString(idx)
    finally:
        if cursor is not None:
            cursor.close()
    return nombre
