# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Campo de texto con corrección ortográfica en español: sugerencias, sin
autocorregir solo. Al pausar de escribir, si la última palabra no se
reconoce, aparece una barra flotante con hasta 3 sugerencias tocables
debajo del campo enfocado (sin cambiar la apariencia del campo). El
usuario elige tocando una sugerencia; si no toca ninguna, el texto se
queda como está."""
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField

from utils.ortografia import sugerencias

_PUNTUACION = '.,;:!?¡¿"\'()'


def _separar_puntuacion(palabra):
    """('reunión,' -> ('', 'reunión', ',')) para poder revisar solo la
    parte alfabética y luego reinsertar la puntuación al reemplazar."""
    inicio = palabra
    prefijo = ''
    while inicio and inicio[0] in _PUNTUACION:
        prefijo += inicio[0]
        inicio = inicio[1:]
    sufijo = ''
    while inicio and inicio[-1] in _PUNTUACION:
        sufijo = inicio[-1] + sufijo
        inicio = inicio[:-1]
    return prefijo, inicio, sufijo


class _BarraSugerencias(MDCard):
    """Overlay compartido (una sola instancia para toda la app) que se
    agrega/quita de Window según haga falta, en vez de vivir dentro del
    layout KV de cada pantalla — así no hay que tocar la fila (lápiz +
    micrófono) de ningún campo ya existente en las 6 pantallas."""

    def __init__(self, **kwargs):
        super().__init__(
            orientation='horizontal',
            adaptive_size=True,
            spacing=dp(6),
            padding=dp(6),
            md_bg_color=(1, 1, 1, 1),
            elevation=8,
            **kwargs,
        )
        self.campo = None

    def mostrar(self, campo, opciones):
        self.campo = campo
        self.clear_widgets()
        for opcion in opciones:
            self.add_widget(MDRaisedButton(
                text=opcion,
                font_size='13sp',
                size_hint_y=None,
                height=dp(36),
                # on_press (toque inicial), no on_release: FocusBehavior
                # desenfoca TODOS los campos enfocados justo despues de
                # CUALQUIER touch_up en la pantalla (ver
                # kivy/uix/behaviors/focus.py::_handle_post_on_touch_up),
                # asi que conviene reemplazar la palabra en cuanto el dedo
                # toca el boton, no esperar a que lo suelte.
                on_press=lambda _inst, o=opcion: self._elegir(o),
            ))
        if self not in Window.children:
            Window.add_widget(self)
        # Reposicionar un frame despues: adaptive_size recalcula
        # self.height de forma diferida (tras el layout de los botones
        # recien agregados), así que leerlo en el mismo tick daría un
        # valor viejo (o 0 la primera vez) y la barra quedaría mal
        # posicionada / superpuesta con el campo.
        Clock.schedule_once(lambda _dt: self._reposicionar(campo), 0)

    def _reposicionar(self, campo):
        if self.campo is not campo:
            return
        x, y = campo.to_window(campo.x, campo.y)
        self.pos = (x, y - self.height - dp(4))

    def ocultar(self, campo=None):
        if campo is not None and self.campo is not campo:
            return
        self.campo = None
        if self in Window.children:
            Window.remove_widget(self)

    def _elegir(self, opcion):
        campo = self.campo
        self.ocultar()
        if campo is not None:
            # Un frame despues, ya resuelto el touch_up completo (incluido
            # el desenfoque global de FocusBehavior), para no competir con
            # el resto del manejo de ese mismo toque.
            Clock.schedule_once(lambda _dt: campo.reemplazar_ultima_palabra(opcion), 0)


_barra = None


def _obtener_barra():
    """Instancia _BarraSugerencias perezosamente, en su primer uso real
    (cuando el usuario ya empezó a escribir), no al importar este módulo:
    los widgets de KivyMD (ThemableBehavior) exigen que la MDApp ya exista,
    y utils/widgets.py se importa desde screens/*.py ANTES de que main.py
    cree la instancia de AgendaApp (import a nivel de módulo, arriba del
    todo del archivo) — instanciar aquí mismo rompía el arranque de la app
    entera con un ValueError de KivyMD."""
    global _barra
    if _barra is None:
        _barra = _BarraSugerencias()
    return _barra


class CampoOrtografico(MDTextField):
    """MDTextField con revisión ortográfica en español. Reemplaza a
    MDTextField en los campos de texto libre (ver utils/ortografia.py para
    el corrector compartido)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._revision_evento = None
        self.bind(text=self._on_text_cambio, focus=self._on_focus_cambio)

    def _on_text_cambio(self, *_args):
        if self._revision_evento is not None:
            self._revision_evento.cancel()
        self._revision_evento = Clock.schedule_once(self._revisar, 0.4)

    def _on_focus_cambio(self, _inst, tiene_foco):
        if tiene_foco:
            return
        if self._revision_evento is not None:
            self._revision_evento.cancel()
            self._revision_evento = None
        _obtener_barra().ocultar(self)

    def _ultima_palabra_cruda(self):
        partes = self.text.split()
        return partes[-1] if partes else ''

    def _revisar(self, _dt):
        crudo = self._ultima_palabra_cruda()
        _prefijo, palabra, _sufijo = _separar_puntuacion(crudo)
        opciones = sugerencias(palabra) if palabra else []
        if opciones and self.focus:
            _obtener_barra().mostrar(self, opciones)
        else:
            _obtener_barra().ocultar(self)

    def reemplazar_ultima_palabra(self, opcion):
        crudo = self._ultima_palabra_cruda()
        if not crudo:
            return
        prefijo, _palabra, sufijo = _separar_puntuacion(crudo)
        texto = self.text
        derecha = texto.rstrip()
        idx = derecha.rfind(crudo)
        if idx == -1:
            return
        reemplazo = prefijo + opcion + sufijo
        self.text = derecha[:idx] + reemplazo + texto[idx + len(crudo):]
