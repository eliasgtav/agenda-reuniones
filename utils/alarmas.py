# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Puente a java_src/.../AlarmasAgenda.java: alarmas de AlarmManager para que
las alertas avisen con la app cerrada o en segundo plano. Fuera de Android
todo es no-op. Ver utils/notificaciones.py::NotificacionesManager para
que alarmas se programan y como se evita avisar dos veces."""
import json
from kivy.utils import platform

_CLASE = 'com.eliasgt.agenda.alarmas.AlarmasAgenda'
# AlarmManager acepta como mucho 500 alarmas por app (lanza excepcion pasado
# eso); con muchas reuniones a futuro basta con las mas proximas -- se
# vuelven a calcular cada vez que se abre o se sale de la app.
MAX_ALARMAS = 60

_ultima_lista = None


def _java():
    from jnius import autoclass
    return (autoclass(_CLASE),
            autoclass('org.kivy.android.PythonActivity').mActivity)


def pedir_permiso_notificaciones():
    # Android 13+ (API 33) no muestra ninguna notificacion -- ni las de
    # plyer con la app abierta ni las de las alarmas -- hasta que el usuario
    # acepta este permiso en tiempo de ejecucion; declararlo en el manifest
    # no alcanza.
    if platform != 'android':
        return
    try:
        from jnius import autoclass
        if autoclass('android.os.Build$VERSION').SDK_INT < 33:
            return
        from android.permissions import check_permission, request_permissions
        permiso = 'android.permission.POST_NOTIFICATIONS'
        if not check_permission(permiso):
            request_permissions([permiso])
    except Exception:
        pass


def sincronizar(alarmas, forzar=False):
    """alarmas: [{clave, rc, t (epoch s), ti, tx, v}]. Reemplaza todas las
    programadas; solo llama a Java si la lista cambio (o forzar=True)."""
    global _ultima_lista
    if platform != 'android':
        return
    alarmas = sorted(alarmas, key=lambda a: a['t'])[:MAX_ALARMAS]
    payload = json.dumps(
        [dict(a, t=int(a['t'] * 1000)) for a in alarmas], ensure_ascii=False)
    if payload == _ultima_lista and not forzar:
        return
    try:
        clase, actividad = _java()
        clase.reemplazarTodas(actividad, payload)
        _ultima_lista = payload
    except Exception:
        pass


def consumir_disparadas():
    """Alarmas que sonaron (notificacion ya mostrada) desde la ultima
    llamada: [{clave, v, t (epoch s)}]."""
    if platform != 'android':
        return []
    try:
        clase, actividad = _java()
        disparadas = json.loads(clase.consumirDisparadas(actividad))
        for d in disparadas:
            d['t'] = d['t'] / 1000
        return disparadas
    except Exception:
        return []
