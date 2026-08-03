# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Campo de texto con corrección ortográfica en español: sugerencias, sin
autocorregir solo. Al pausar de escribir, si la última palabra no se
reconoce, aparece una barra flotante con hasta 3 sugerencias tocables
debajo del campo enfocado (sin cambiar la apariencia del campo). El
usuario elige tocando una sugerencia; si no toca ninguna, el texto se
queda como está."""
import re
from time import time

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import platform
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField

from utils.ortografia import sugerencias
from utils import teclado

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
        self._reposicion_evento = None

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
        # Reposicionar en un intervalo, no una sola vez: (a) adaptive_size
        # recalcula self.height de forma diferida (tras el layout de los
        # botones recien agregados), asi que leerlo en el mismo tick daria
        # un valor viejo (o 0 la primera vez); (b) la altura del teclado
        # (ver utils/teclado.py) se mide por polling y puede seguir
        # cambiando mientras el teclado termina de animarse hacia arriba.
        if self._reposicion_evento is not None:
            self._reposicion_evento.cancel()
        self._reposicion_evento = Clock.schedule_interval(
            lambda _dt: self._reposicionar(campo), 0.15
        )

    def _reposicionar(self, campo):
        if self.campo is not campo:
            return
        if platform == 'android':
            # En Android, Window.softinput_mode ("below_target", puesto en
            # main.py) NO hace nada con el bootstrap SDL2 -- Window.
            # keyboard_height siempre da 0 ahi (confirmado en el codigo
            # fuente de Kivy), asi que Kivy nunca reacomoda nada por su
            # cuenta. Por eso NO conviene usar la posicion del campo
            # (campo.to_window) como respaldo: si el campo es grande y
            # esta bajo en la pantalla, esa posicion puede quedar detras
            # del teclado. En vez de eso, siempre se pega la barra al
            # teclado medido (utils/teclado.py); si todavia no hay una
            # medicion (el polling de 0.3s no alcanzo a correr, o el
            # campo acaba de recibir foco hace un instante), se asume una
            # altura conservadora mientras el campo siga enfocado, en vez
            # de caer detras de donde probablemente este el teclado.
            alto_teclado = teclado.altura_teclado()
            if alto_teclado <= 0 and campo.focus:
                alto_teclado = Window.height * 0.35
            self.adaptive_width = False
            self.width = Window.width
            self.pos = (0, alto_teclado)
        else:
            self.adaptive_width = True
            x, y = campo.to_window(campo.x, campo.y)
            self.pos = (x, y - self.height - dp(4))

    def ocultar(self, campo=None):
        if campo is not None and self.campo is not campo:
            return
        self.campo = None
        if self._reposicion_evento is not None:
            self._reposicion_evento.cancel()
            self._reposicion_evento = None
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
        self._ultimo_toque_ts = 0
        self._ultimo_toque_pos = None
        self.bind(text=self._on_text_cambio, focus=self._on_focus_cambio)

    def on_touch_down(self, touch):
        consumido = super().on_touch_down(touch)
        if self.collide_point(*touch.pos):
            # Deteccion propia de doble toque (no touch.is_double_tap): en
            # pantalla tactil real el segundo dedo casi nunca cae en el
            # mismo pixel que el primero, y el umbral de distancia por
            # defecto de Kivy (pensado para mouse) es demasiado estricto,
            # asi que el doble-tap para seleccionar palabra fallaba en el
            # telefono aunque funcionara con mouse en escritorio.
            ahora = time()
            anterior_ts = self._ultimo_toque_ts
            anterior_pos = self._ultimo_toque_pos
            self._ultimo_toque_ts = ahora
            self._ultimo_toque_pos = touch.pos
            if (
                anterior_pos is not None
                and ahora - anterior_ts < 0.4
                and abs(touch.x - anterior_pos[0]) < dp(40)
                and abs(touch.y - anterior_pos[1]) < dp(40)
            ):
                self._ultimo_toque_ts = 0
                self._ultimo_toque_pos = None
                self._select_word()
        return consumido

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
        # Kivy no reubica self.cursor al cambiar self.text a mano: si se
        # deja apuntando a la posicion vieja (p.ej. porque "opcion" es mas
        # corta que "crudo"), la siguiente tecla que el usuario escriba
        # hace que TextInput.insert_text indexe una fila que ya no existe
        # y crashea con IndexError. Se reubica al final de la palabra
        # reemplazada, que es donde el usuario esperaria seguir escribiendo.
        self.cursor = self.get_cursor_from_index(idx + len(reemplazo))


class CampoOraciones(CampoOrtografico):
    """CampoOrtografico que ademas pone en mayúscula la primera letra de
    cada oración (inicio del texto, o tras '.', '!', '?' o un salto de
    línea) a medida que se escribe. Se implementa sobre insert_text (el
    mismo mecanismo que usa Kivy para insertar cada tecla/IME), no
    reasignando self.text, para no repetir el bug de cursor desincronizado
    de reemplazar_ultima_palabra."""

    def insert_text(self, substring, from_undo=False):
        if substring and not from_undo and self._inicia_oracion():
            substring = substring[0].upper() + substring[1:]
        return super().insert_text(substring, from_undo=from_undo)

    def _inicia_oracion(self):
        antes = self.text[:self.cursor_index()].rstrip(' \t')
        return not antes or antes[-1] in '.!?\n'


def _mayuscula_inicial(texto):
    return texto[0].upper() + texto[1:] if texto else texto


class CampoAcuerdosNumerados(CampoOraciones):
    """Cada línea se numera sola (1.- , 2.- , ...) a medida que se escribe,
    para llevar los acuerdos de la reunión como una lista numerada dentro
    del mismo campo, sin diálogo ni pantalla aparte. Enter en una línea
    numerada vacía (el usuario no escribió nada) apaga la numeración de
    forma permanente para el resto del texto -- pensado para cuando ya
    terminó de listar acuerdos y quiere seguir escribiendo notas libres."""

    def __init__(self, **kwargs):
        self._numerando = True
        super().__init__(**kwargs)
        self.bind(focus=self._on_focus_numerado, text=self._on_text_numerado)

    def reiniciar_numeracion(self):
        """Llamar al cargar una reunión distinta en este mismo campo (el
        widget se reutiliza entre reuniones): sin esto, apagar la
        numeración en una reunión la dejaría apagada también en las
        siguientes que se abran con este mismo campo."""
        self._numerando = True

    def _on_text_numerado(self, _inst, texto):
        # Si el usuario borra todo el texto visible, cuenta como "empezar
        # de nuevo": reactiva la numeración aunque un doble Enter anterior
        # la hubiera apagado. Puede quedar una o más líneas en blanco sin
        # texto real (p.ej. al borrar con retroceso no siempre se llega
        # hasta un self.text == '' exacto) -- eso también hacía que
        # insert_text nunca viera "self.text vacío" y no renumerara. Se
        # limpian esas líneas en blanco solas, en el siguiente frame (no
        # de inmediato: seguir editando self.text en medio del borrado que
        # disparó este evento reentra en el propio TextInput y puede
        # desincronizar el cursor).
        if not texto.strip():
            self._numerando = True
            if texto:
                Clock.schedule_once(self._limpiar_lineas_vacias, 0)

    def _limpiar_lineas_vacias(self, _dt):
        if self.text and not self.text.strip():
            self.select_text(0, len(self.text))
            self.delete_selection()

    def _on_focus_numerado(self, _inst, tiene_foco):
        # Sembrar el "1.- " al enfocar un campo vacío, ANTES de que llegue
        # cualquier texto real (así no depende de si el primer texto llega
        # caracter por caracter, en un solo bloque por voz, o pegado). Se
        # llama directo al insert_text de TextInput (sin pasar por el de
        # esta clase ni el de CampoOraciones) para no reentrar en la propia
        # lógica de numerado de abajo y duplicar el número ("1.- 1.- ...").
        if tiene_foco and self._numerando and not self.text:
            from kivy.uix.textinput import TextInput
            TextInput.insert_text(self, '1.- ')

    def insert_text(self, substring, from_undo=False):
        if not self._numerando or from_undo:
            return super().insert_text(substring, from_undo=from_undo)

        if substring == '\n':
            linea_actual = self._linea_actual()
            if re.fullmatch(r'\d+\.- ', linea_actual):
                # Línea numerada vacía: se quita ese número y se apaga la
                # numeración en vez de abrir otra línea numerada más.
                fin = self.cursor_index()
                inicio = fin - len(linea_actual)
                self.select_text(inicio, fin)
                self.delete_selection()
                self._numerando = False
                return super().insert_text('\n', from_undo=from_undo)

        if substring:
            partes = substring.split('\n')
            numero = self._siguiente_numero()
            # La línea donde está el cursor está vacía en este momento --
            # ya sea porque el campo entero está vacío (recién enfocado
            # sin haber alcanzado a sembrar el "1.- " a tiempo, o borrado
            # todo sin volver a salir del campo), o porque el usuario
            # borró un acuerdo puntual (número incluido) para corregirlo y
            # sigue escribiendo en esa misma línea: en ambos casos, numerar
            # la línea que está por empezar. La mayúscula inicial se aplica
            # aquí mismo (no dejarla para el _inicia_oracion de
            # CampoOraciones): ese sólo mira substring[0], que en este
            # punto ya es el número antepuesto, no la letra real.
            if not self._linea_actual() and partes[0].strip():
                partes[0] = f'{numero}.- {_mayuscula_inicial(partes[0])}'
                numero += 1
            # Cualquier salto de línea dentro de lo insertado (Enter, o
            # texto con varias líneas pegado/dictado de una sola vez)
            # numera la línea siguiente (misma razón: mayúscula aplicada
            # aquí mismo).
            for i in range(1, len(partes)):
                partes[i] = f'{numero}.- {_mayuscula_inicial(partes[i])}'
                numero += 1
            substring = '\n'.join(partes)
        return super().insert_text(substring, from_undo=from_undo)

    def _inicia_oracion(self):
        # Además de inicio de texto / tras '.', '!', '?' o salto de línea
        # (comportamiento heredado): también justo después del "N.- " que
        # se antepone solo, para que la primera letra de cada acuerdo
        # también salga en mayúscula.
        if super()._inicia_oracion():
            return True
        if not self._numerando:
            return False
        antes = self.text[:self.cursor_index()]
        return bool(re.search(r'\d+\.- $', antes))

    def _linea_actual(self):
        antes = self.text[:self.cursor_index()]
        inicio = antes.rfind('\n') + 1
        return antes[inicio:]

    def _siguiente_numero(self):
        numeros = []
        for linea in self.text.split('\n'):
            m = re.match(r'^(\d+)\.- ', linea)
            if m:
                numeros.append(int(m.group(1)))
        return (max(numeros) + 1) if numeros else 1
