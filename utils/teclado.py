# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Altura del teclado nativo de Android, para poder posicionar overlays
de Kivy (p.ej. la barra de sugerencias ortográficas) justo encima de él,
como el panel de sugerencias de WhatsApp.

Window.keyboard_height de Kivy siempre devuelve 0 con el bootstrap SDL2
de Android ("Placeholder until the SDL2 bootstrap supports this", ver
kivy/core/window/__init__.py::_get_android_kheight), así que hay que
leerla directo del lado Java: se compara el alto total de la pantalla
contra el área visible que reporta la ventana (WindowVisibleDisplayFrame),
la diferencia es lo que ocupa el teclado."""
from kivy.utils import platform
from kivy.clock import Clock

_altura_actual = 0
_intervalo_evento = None


def altura_teclado():
    """Ultima altura medida del teclado en pixeles de Window (0 = oculto,
    o no estamos en Android) -- puede estar hasta 0.3s desatrasada, ver
    medir_ahora() para una lectura fresca sin esperar al siguiente tick
    del polling."""
    return _altura_actual


def _calcular():
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Rect = autoclass('android.graphics.Rect')
        decor = PythonActivity.mActivity.getWindow().getDecorView()
        r = Rect()
        decor.getWindowVisibleDisplayFrame(r)
        alto_total = decor.getRootView().getHeight()
        alto_teclado = alto_total - r.bottom()
        # Umbral para no confundir barras de sistema/notch con teclado.
        return alto_teclado if alto_teclado > alto_total * 0.15 else 0
    except Exception:
        return 0


def _medir(_dt):
    global _altura_actual
    _altura_actual = _calcular()


def medir_ahora():
    """Mide la altura del teclado en este instante (mismo cálculo que el
    polling de fondo, pero sin esperar al siguiente tick de 0.3s) -- para
    quien necesite la lectura más fresca posible, como _BarraSugerencias
    reposicionándose justo cuando aparece: esperar al polling de fondo
    podía dar un valor viejo (0, con el teclado ya abierto) justo en ese
    primer instante, y el respaldo por defecto (fracción fija de
    Window.height) resultaba más chico que el teclado real -- la barra
    quedaba tapada hasta que el siguiente tick del polling la corregía
    sola un momento después (bug real reportado por el usuario con
    capturas de pantalla)."""
    global _altura_actual
    _altura_actual = _calcular()
    return _altura_actual


def iniciar_monitoreo():
    """Empieza a medir la altura del teclado cada 0.3s (solo Android, no
    hace nada en escritorio). Llamar una sola vez, desde on_start."""
    global _intervalo_evento
    if platform != 'android' or _intervalo_evento is not None:
        return
    _intervalo_evento = Clock.schedule_interval(_medir, 0.3)
