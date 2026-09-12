# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Campo de texto con corrección ortográfica propia (barra de sugerencias
pegada al teclado, dibujada por la app -- ver _BarraSugerencias abajo).

Se probó delegar esto al teclado nativo (Gboard/SwiftKey, commit
`785e7b0`) pero se revirtió (ver memoria project_agenda_bug_teclado_
duplicado): el puente SDLInputConnection que arma python-for-android no
implementa los métodos que Gboard necesita para reemplazar una palabra con
seguridad (getTextBeforeCursor/setComposingRegion/etc.), así que tocar una
sugerencia nativa a veces no hacía nada y a veces pegaba el texto nuevo
mal calculado sobre el viejo. Con una barra propia el reemplazo lo hace
la app en Python, sin depender de esa conexión rota."""
import re
from time import monotonic as time

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
    micrófono) de ningún campo ya existente."""

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
        # Reposicionar ya mismo (evita un primer frame en la posicion
        # vieja de la vez anterior, o en (0,0) la primera vez) Y ademas en
        # un intervalo: (a) adaptive_size recalcula self.height de forma
        # diferida (tras el layout de los botones recien agregados), asi
        # que leerlo en el mismo tick daria un valor viejo (o 0 la primera
        # vez); (b) la altura del teclado (ver utils/teclado.py) puede
        # seguir cambiando mientras el teclado termina de animarse hacia
        # arriba.
        self._reposicionar(campo)
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
            # teclado medido (utils/teclado.py). Se pide una medicion
            # FRESCA (medir_ahora, no el ultimo valor del polling de
            # fondo): el polling corre cada 0.3s, y justo en el primer
            # instante en que aparece la barra podia devolver un valor
            # viejo (0, con el teclado ya abierto) -- el respaldo de ese
            # caso (fraccion fija de Window.height) resultaba mas chico
            # que el teclado real y la barra quedaba tapada hasta que el
            # siguiente tick del polling la corregia sola un momento
            # despues (bug real reportado con capturas de pantalla). Si
            # aun asi la medicion fresca da 0 (campo recien enfocado,
            # teclado todavia animando hacia arriba), se asume una altura
            # conservadora mientras el campo siga enfocado.
            alto_teclado = teclado.medir_ahora()
            if alto_teclado <= 0 and campo.focus:
                alto_teclado = Window.height * 0.5
            self.adaptive_width = False
            self.width = Window.width
            self.pos = (0, alto_teclado)
        else:
            # En escritorio no hay teclado que tape nada, pero en campos
            # multilínea que crecen hacia abajo (Desarrollo/Objetivos/
            # Acuerdos, área de captura de En Reunión) el cursor -- y la
            # palabra que se está escribiendo -- casi siempre queda pegado
            # al BORDE INFERIOR del campo, justo donde antes se ponía la
            # barra ("y - self.height - dp(4)", debajo del campo pero
            # encima de lo que sea que venga después en el layout): en la
            # práctica tapaba la palabra recién escrita. Ahora se ancla
            # ARRIBA del campo en vez de abajo -- nunca se solapa con el
            # texto que vive DENTRO del campo, sin importar en qué línea
            # esté el cursor.
            self.adaptive_width = True
            x, top = campo.to_window(campo.x, campo.top)
            arriba = top + dp(4)
            if arriba + self.height > Window.height:
                # No cabe arriba (campo pegado al borde superior de la
                # ventana) -> mejor debajo del campo que cortado por fuera.
                _, base = campo.to_window(campo.x, campo.y)
                arriba = base - self.height - dp(4)
            x = max(0, min(x, Window.width - self.width))
            self.pos = (x, arriba)

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

# Instrumentación temporal que permitió diagnosticar en dispositivo real el
# bug de duplicación de texto con el teclado nativo (ver memoria
# project_agenda_bug_teclado_duplicado): confirmó que Gboard arrastraba
# texto ya borrado al siguiente commit, resuelto forzando
# _restart_input_android() en do_backspace/delete_selection. Se deja el
# código de logging en el archivo (por si hace falta reabrir el diagnóstico
# de algo relacionado) pero apagado -- no debe loguear cada tecla en
# producción.
_DEBUG_TECLADO = False  # DIAGNOSTICO -- NUNCA dejar en True fuera de una sesión
                        # de diagnóstico puntual: cada tecla en CUALQUIER
                        # campo de texto de la app dispara varias escrituras a
                        # disco (key_down/up, do_backspace, insert_text,
                        # tick...) -- con esto en True se vio la app ponerse
                        # lenta y llegar a congelarse varios segundos al
                        # mantener presionado Backspace (escritorio,
                        # 2026-09-10, probablemente antivirus interceptando
                        # cada escritura rápida al archivo de log).


def _log_teclado(mensaje_fn):
    # mensaje_fn es una funcion (normalmente `lambda: f'...'`), no un string
    # ya armado -- con _DEBUG_TECLADO en False (el caso normal en
    # produccion) esto evita construir los f-strings de diagnostico en CADA
    # tecla presionada en CUALQUIER campo de texto de la app (todos heredan
    # de CampoOrtografico). Antes el string se armaba siempre en el
    # call site, sin importar que _log_teclado lo fuera a descartar.
    if not _DEBUG_TECLADO:
        return
    try:
        from datetime import datetime
        import os
        try:
            from android.storage import app_storage_path
            base = app_storage_path()
        except Exception:
            base = os.path.expanduser('~')
        ruta = os.path.join(base, 'teclado_debug.log')
        with open(ruta, 'a', encoding='utf-8') as f:
            f.write(f'[{datetime.now().isoformat()}] {mensaje_fn()}\n')
    except Exception:
        pass


def _restart_input_android(_dt=None):
    """Causa raíz confirmada con logging real en dispositivo (ver memoria
    project_agenda_bug_teclado_duplicado): cuando la app borra texto del
    lado de Kivy (retroceso, selección), nunca se lo avisa a la conexión
    real de Android con el teclado -- Gboard sigue creyendo que el texto
    viejo sigue ahí, y en el siguiente commit devuelve una mezcla del
    resto que YA se había borrado más lo nuevo que se escribió (visto en
    el log: campo con 'EL', Gboard mandó 'ias Gaytán eli' -- el resto de
    'Gaytán' que ya no estaba, pegado con 'eli' recién tecleado). Forzar
    InputMethodManager.restartInput() tira el estado interno viejo de
    Gboard para que la próxima palabra se calcule contra el texto real."""
    if platform != 'android':
        return
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Context = autoclass('android.content.Context')
        activity = PythonActivity.mActivity
        vista = activity.getCurrentFocus() or activity.getWindow().getDecorView()
        imm = activity.getSystemService(Context.INPUT_METHOD_SERVICE)
        imm.restartInput(vista)
        _log_teclado(lambda: f'_restart_input_android OK vista={vista!r}')
    except Exception as e:
        _log_teclado(lambda: f'_restart_input_android EXCEPCION {e!r}')


def _programar_restart_input():
    # Debounced: una ráfaga de varios retrocesos seguidos (mantener
    # presionado) solo debe disparar UN restart, justo después del último,
    # no uno por cada tecla -- restartInput() es una operación pesada del
    # lado de Android. No aplica fuera de Android -- evita programar un
    # Clock event (y la excepción de jnius que _restart_input_android
    # atrapa) en cada borrado en escritorio.
    if platform != 'android':
        return
    Clock.unschedule(_restart_input_android)
    Clock.schedule_once(_restart_input_android, 0.05)


# ── Borrado acelerado al mantener pulsado Backspace ───────────────────────
# En Android con el bootstrap SDL2 el teclado corre en modo "generar eventos
# de tecla" (input_type='null', ver docstring de CampoOrtografico) y el
# hold-to-delete acelerado propio de Gboard/teclado de iOS no siempre llega
# a la app -- mantener pulsado el retroceso borraba a un ritmo lento y
# constante. Este mixin lo implementa del lado de la app, como el
# hold-to-delete nativo de WhatsApp/EditText: siempre carácter por carácter
# (nunca salta a borrar palabras completas), empezando lento y acelerando
# gradualmente mientras se mantiene presionado.
_BKSP_KEYCODE = 8                  # 'backspace' en los keycodes de Kivy
_BKSP_INTERVALO_INICIAL = 0.35     # ritmo al empezar a mantener pulsado
_BKSP_INTERVALO_MIN = 0.08         # ritmo tope tras acelerar
_BKSP_ACELERACION_DURACION = 3.0   # segundos para llegar del ritmo inicial al tope
_BKSP_VERIFICAR_LIBERACION = 0.12  # tras un key_up, cuanto esperar antes de
                                    # confirmar que fue un toque suelto (ver
                                    # docstring de la clase)
_BKSP_LIBERAR = 0.55           # red de respaldo: sin key_down por este
                                # tiempo => tecla soltada (por si nunca
                                # llega key_up, p.ej. se pierde el foco)
_BKSP_MAX_SOSTENIDO = 20        # red de seguridad dura


class BorradoAcelerado:
    """Mixin para (MD)TextInput: mantener pulsado Backspace acelera el
    borrado. SOLO actúa en Android -- ahí el teclado corre en modo
    "generar eventos de tecla" (ver docstring de CampoOrtografico) y el
    hold-to-delete acelerado propio de Gboard no siempre llega a la app,
    así que hace falta reimplementarlo del lado de Python con un Clock
    propio. Mantener pulsado el retroceso genera una ráfaga de eventos
    key_down/key_up sintéticos al ritmo (ya acelerado) de Gboard -- si
    dejáramos que cada uno borrara, el borrado saldría "de golpe". Los
    key_down solo cuentan como "sigo pulsando" (refrescan
    _bksp_last_down); un key_up programa una verificación corta
    (_BKSP_VERIFICAR_LIBERACION): si no llega un key_down nuevo en ese
    lapso, se confirma que la tecla ya se soltó y se para ahí (evita que un
    toque suelto borre de más). Si sí llega un key_down nuevo (el patrón de
    ráfaga real de Gboard), la verificación no hace nada y el borrado sigue
    al ritmo del Clock. _BKSP_LIBERAR queda como red de respaldo por si un
    key_up se pierde del todo (p.ej. al perder el foco a media pulsación).

    ESCRITORIO: no se toca nada, letra por letra, al ritmo nativo de
    key-repeat de Windows -- a pedido explícito del usuario tras probar
    variantes con aceleración propia (por Clock y por evento) que en este
    entorno se sintieron "de golpe" o inconsistentes (ver historial de
    commits de esta función). No asumir que hace falta "arreglar" esto: es
    el comportamiento pedido, no un placeholder."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._bksp_evento = None
        self._bksp_t0 = 0.0
        self._bksp_last_down = 0.0
        self.bind(focus=self._bksp_on_focus)

    def _id_log(self):
        # CampoOrtografico lo sobrescribe; esto cubre a CampoSimple.
        return getattr(self, 'hint_text', '') or f'campo{id(self) % 10000}'

    def _bksp_on_focus(self, _inst, tiene_foco):
        if not tiene_foco:
            self._bksp_detener()

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        mods = set(modifiers) - {'capslock', 'numlock', 'shift'}
        es_backspace = (
            keycode[0] == _BKSP_KEYCODE
            and not mods
            and not self.readonly
            and not self.disabled
        )
        if es_backspace and platform == 'android':
            ahora = time()
            self._bksp_last_down = ahora
            if self._bksp_evento is None:
                self._bksp_t0 = ahora
                self._bksp_borrar()
                self._bksp_evento = Clock.schedule_once(
                    self._bksp_tick, _BKSP_INTERVALO_INICIAL
                )
            _log_teclado(lambda:
                f'{self._id_log()} BKSP key_down ahora={ahora:.3f} '
                f'evento={"si" if self._bksp_evento else "no"} texto={self.text!r}'
            )
            # Consumir: el auto-repeat lo lleva el Clock, no do_backspace de
            # Kivy ni el key-repeat de SDL/Android.
            return True
        # Escritorio: sin interceptar nada -- cada key_down real de
        # Windows (a su propio ritmo de key-repeat nativo) borra
        # exactamente un carácter vía el do_backspace() por defecto de
        # Kivy/TextInput, letra por letra, sin ningún multiplicador propio
        # (se probaron variantes con aceleración -- por evento y por
        # Clock -- y en este entorno se sintieron siempre "de golpe" o
        # inconsistentes; el usuario pidió explícitamente letra por letra,
        # así que la app ya no toca este camino para nada en escritorio).
        return super().keyboard_on_key_down(window, keycode, text, modifiers)

    def keyboard_on_key_up(self, window, keycode):
        if platform == 'android' and keycode[0] == _BKSP_KEYCODE:
            t_up = time()
            _log_teclado(lambda:
                f'{self._id_log()} BKSP key_up t={t_up:.3f}, '
                f'verificar en {_BKSP_VERIFICAR_LIBERACION}s'
            )
            Clock.schedule_once(
                lambda _dt: self._bksp_verificar_liberacion(t_up),
                _BKSP_VERIFICAR_LIBERACION,
            )
        return super().keyboard_on_key_up(window, keycode)

    def _bksp_verificar_liberacion(self, t_up):
        # Si no llegó ningún key_down nuevo después de este key_up, la
        # tecla ya está soltada de verdad -- parar ya, sin esperar
        # _BKSP_LIBERAR completo (eso es lo que causaba el borrado de dos
        # caracteres en un solo toque: el primer tick programado podía
        # disparar antes de que ese timeout largo se cumpliera).
        if self._bksp_last_down <= t_up:
            _log_teclado(lambda:
                f'{self._id_log()} BKSP verificar_liberacion: '
                f'confirmado soltado (last_down={self._bksp_last_down:.3f} '
                f'<= t_up={t_up:.3f})'
            )
            self._bksp_detener()
        else:
            _log_teclado(lambda:
                f'{self._id_log()} BKSP verificar_liberacion: sigue '
                f'presionada (last_down={self._bksp_last_down:.3f} > '
                f't_up={t_up:.3f}), no para'
            )

    def _bksp_tick(self, _dt):
        ahora = time()
        sostenido = ahora - self._bksp_t0
        if (
            not self.focus
            or ahora - self._bksp_last_down > _BKSP_LIBERAR
            or sostenido > _BKSP_MAX_SOSTENIDO
        ):
            _log_teclado(lambda:
                f'{self._id_log()} BKSP stop foco={self.focus} '
                f'gap={ahora - self._bksp_last_down:.3f} sostenido={sostenido:.2f}'
            )
            self._bksp_detener()
            return
        if not self._bksp_borrar():
            self._bksp_detener()
            return
        avance = min(sostenido / _BKSP_ACELERACION_DURACION, 1.0)
        proximo = _BKSP_INTERVALO_INICIAL - (
            _BKSP_INTERVALO_INICIAL - _BKSP_INTERVALO_MIN
        ) * avance
        _log_teclado(lambda:
            f'{self._id_log()} BKSP tick borro sostenido={sostenido:.3f} '
            f'proximo={proximo:.3f} texto={self.text!r}'
        )
        self._bksp_evento = Clock.schedule_once(self._bksp_tick, proximo)

    def _bksp_detener(self):
        if self._bksp_evento is not None:
            self._bksp_evento.cancel()
            self._bksp_evento = None

    def _bksp_borrar(self):
        """Borra un carácter hacia atrás. Devuelve True si algo cambió."""
        antes = self.text
        if self.selection_text:
            self.delete_selection()
            return self.text != antes
        if self.cursor_index() <= 0:
            return False
        self.do_backspace()
        return self.text != antes


class CampoOrtografico(BorradoAcelerado, MDTextField):
    """MDTextField con corrección ortográfica en español vía barra propia
    (ver _BarraSugerencias arriba y utils/ortografia.py para el corrector
    compartido). No fija input_type='text' a propósito -- eso activaría
    ADEMÁS la franja nativa de sugerencias de Gboard, que en este puente
    SDL2 no reemplaza el texto de forma confiable (ver docstring del
    módulo); dejar input_type en su valor por defecto ('null') evita que
    aparezcan dos franjas de sugerencias compitiendo, una funcional
    (la propia) y otra rota (la nativa)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ultimo_toque_ts = 0
        self._ultimo_toque_pos = None
        self._revision_evento = None
        self.bind(text=self._on_text_cambio, focus=self._on_focus_cambio)

    def _id_log(self):
        return getattr(self, 'hint_text', '') or f'campo{id(self) % 10000}'

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
        derecha = self.text.rstrip()
        idx = derecha.rfind(crudo)
        if idx == -1:
            return
        reemplazo = prefijo + opcion + sufijo
        # Seleccionar+borrar+insert_text (NO asignar self.text a mano):
        # asi el reemplazo pasa por el insert_text de la subclase
        # (CampoMayusculas/CampoOraciones/CampoAcuerdosNumerados) y
        # respeta mayusculas/numeracion igual que si se hubiera escrito a
        # mano -- bug real reportado por el usuario con capturas de
        # pantalla: el reemplazo quedaba tal cual la sugerencia (en
        # minusculas) en campos que fuerzan mayuscula, porque asignar
        # self.text saltaba por completo esa logica. insert_text tambien
        # reubica self.cursor solo, sin el calculo manual que hacia esto
        # antes.
        self.select_text(idx, idx + len(crudo))
        self.delete_selection()
        self.insert_text(reemplazo)

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

    def window_on_textedit(self, window, text):
        # Kivy llama esto por cada evento de "composición" IME que manda
        # Android (SDL2) mientras Gboard va sugiriendo/autocorrigiendo la
        # palabra en curso, ANTES de que se confirme -- ver
        # keyboard_on_textinput abajo. Instrumentado (sin tocar lógica)
        # para ver la secuencia real de eventos en dispositivo.
        _log_teclado(lambda:
            f'{self._id_log()} window_on_textedit IN text={text!r} '
            f'ime_comp_antes={self._ime_composition!r} '
            f'ime_cursor_antes={self._ime_cursor!r} '
            f'texto_antes={self.text!r} cursor_antes={self.cursor!r}'
        )
        super().window_on_textedit(window, text)
        _log_teclado(lambda:
            f'{self._id_log()} window_on_textedit OUT '
            f'ime_comp_despues={self._ime_composition!r} '
            f'ime_cursor_despues={self._ime_cursor!r} '
            f'texto_despues={self.text!r} cursor_despues={self.cursor!r}'
        )

    def keyboard_on_textinput(self, window, text):
        # El teclado nativo (Gboard) muestra la palabra que se está
        # escribiendo/autocorrigiendo como "composición" IME -- Kivy la va
        # insertando de forma directa en window_on_textedit, fuera de
        # insert_text. Cuando esa palabra se CONFIRMA (con espacio,
        # puntuación, o al tocar una sugerencia), Android puede reenviar
        # la palabra completa en el commit en vez de solo lo nuevo -- si
        # no se borra primero el residuo de la composición ya insertada,
        # queda duplicada ("holahola"). Bug real reportado por el
        # usuario y reproducido con un script aislado: commitText('Hola ')
        # sobre una composición 'hola' sin limpiar daba 'holaHola '.
        _log_teclado(lambda:
            f'{self._id_log()} keyboard_on_textinput IN text={text!r} '
            f'ime_comp_antes={self._ime_composition!r} '
            f'ime_cursor_antes={self._ime_cursor!r} '
            f'texto_antes={self.text!r} cursor_antes={self.cursor!r}'
        )
        self._limpiar_residuo_ime()
        _log_teclado(lambda:
            f'{self._id_log()} keyboard_on_textinput tras_limpiar_residuo '
            f'texto={self.text!r} cursor={self.cursor!r}'
        )
        super().keyboard_on_textinput(window, text)
        self._ime_composition = ''
        _log_teclado(lambda:
            f'{self._id_log()} keyboard_on_textinput OUT '
            f'texto_despues={self.text!r} cursor_despues={self.cursor!r}'
        )

    def _limpiar_residuo_ime(self):
        comp = self._ime_composition
        cursor_comp = self._ime_cursor
        if not comp or not cursor_comp:
            _log_teclado(lambda:
                f'{self._id_log()} _limpiar_residuo_ime SKIP '
                f'(comp={comp!r} cursor_comp={cursor_comp!r})'
            )
            return
        pcc, pcr = cursor_comp
        lines = self._lines
        if pcr >= len(lines):
            _log_teclado(lambda:
                f'{self._id_log()} _limpiar_residuo_ime SKIP '
                f'(pcr={pcr!r} fuera de rango, len(lines)={len(lines)!r})'
            )
            return
        linea = lines[pcr]
        if linea[pcc - len(comp):pcc] != comp:
            _log_teclado(lambda:
                f'{self._id_log()} _limpiar_residuo_ime SKIP '
                f'(linea[{pcc - len(comp)}:{pcc}]={linea[pcc - len(comp):pcc]!r} '
                f'!= comp={comp!r})'
            )
            return
        ci = self.cursor_index()
        nueva_linea = linea[:pcc - len(comp)] + linea[pcc:]
        self._refresh_text_from_property(
            "insert", *self._get_line_from_cursor(pcr, nueva_linea)
        )
        self.cursor = self.get_cursor_from_index(max(0, ci - len(comp)))
        _log_teclado(lambda:
            f'{self._id_log()} _limpiar_residuo_ime APLICADO '
            f'comp={comp!r} linea_antes={linea!r} linea_despues={nueva_linea!r}'
        )

    def insert_text(self, substring, from_undo=False):
        # Único punto de esta clase base donde se loguea insert_text: las
        # subclases (CampoMayusculas/CampoOraciones/CampoAcuerdosNumerados)
        # transforman `substring` (mayúsculas, numeración) y llaman a
        # super().insert_text(...) en cadena hasta llegar aquí, así que este
        # log ya muestra el substring final tal como se inserta de verdad.
        texto_antes = self.text
        cursor_antes = self.cursor
        resultado = super().insert_text(substring, from_undo=from_undo)
        _log_teclado(lambda:
            f'{self._id_log()} insert_text substring={substring!r} '
            f'from_undo={from_undo!r} texto_antes={texto_antes!r} '
            f'cursor_antes={cursor_antes!r} texto_despues={self.text!r} '
            f'cursor_despues={self.cursor!r}'
        )
        return resultado

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        # El primer log real en dispositivo mostró que window_on_textedit
        # NUNCA se llama (el residuo de composición IME no es el problema
        # real acá). Este es el siguiente sospechoso: TextInput.
        # keyboard_on_key_down interpreta texto que empieza con
        # chr(1)/chr(2) como un CANAL DE COMANDOS aparte (ver
        # TextInput._handle_command en el código fuente de Kivy -- "DEL:N"
        # para borrar, "INSERT:"/"INSERTN:" para insertar, "SELWORD",
        # "CURCOL", etc.), completamente por fuera de keyboard_on_textinput/
        # insert_text ya instrumentados arriba. Si Android manda backspace o
        # reemplazos de sugerencia por este canal, no aparecía en el log
        # anterior. Se loguea el texto crudo tal cual llega (repr, para ver
        # los caracteres de control si los hay) antes de que Kivy lo
        # interprete.
        _log_teclado(lambda:
            f'{self._id_log()} keyboard_on_key_down IN keycode={keycode!r} '
            f'text={text!r} modifiers={modifiers!r} '
            f'texto_antes={self.text!r} cursor_antes={self.cursor!r} '
            f'seleccion_antes=({self._selection_from!r},{self._selection_to!r})'
        )
        resultado = super().keyboard_on_key_down(window, keycode, text, modifiers)
        _log_teclado(lambda:
            f'{self._id_log()} keyboard_on_key_down OUT '
            f'texto_despues={self.text!r} cursor_despues={self.cursor!r} '
            f'seleccion_despues=({self._selection_from!r},{self._selection_to!r})'
        )
        return resultado

    def delete_selection(self, from_undo=False):
        texto_antes = self.text
        cursor_antes = self.cursor
        seleccion = (self._selection_from, self._selection_to)
        resultado = super().delete_selection(from_undo=from_undo)
        if self.text != texto_antes:
            _programar_restart_input()
        _log_teclado(lambda:
            f'{self._id_log()} delete_selection from_undo={from_undo!r} '
            f'seleccion={seleccion!r} texto_antes={texto_antes!r} '
            f'cursor_antes={cursor_antes!r} texto_despues={self.text!r} '
            f'cursor_despues={self.cursor!r}'
        )
        return resultado

    def do_backspace(self, from_undo=False, mode='bkspc'):
        texto_antes = self.text
        cursor_antes = self.cursor
        resultado = super().do_backspace(from_undo=from_undo, mode=mode)
        if self.text != texto_antes:
            _programar_restart_input()
        _log_teclado(lambda:
            f'{self._id_log()} do_backspace from_undo={from_undo!r} '
            f'mode={mode!r} texto_antes={texto_antes!r} '
            f'cursor_antes={cursor_antes!r} texto_despues={self.text!r} '
            f'cursor_despues={self.cursor!r}'
        )
        return resultado


class CampoMayusculas(CampoOrtografico):
    """CampoOrtografico que convierte a mayúsculas todo lo que se escribe,
    implementado sobre insert_text (no reasignando self.text a mano: eso
    dispara internamente self.cursor = fin-del-texto en CADA cambio, lo
    que descoloca el reemplazo de sugerencias del teclado nativo -- ver
    memoria project_agenda_bug_ontext_reentrancy)."""

    def insert_text(self, substring, from_undo=False):
        if substring and not from_undo:
            substring = substring.upper()
        return super().insert_text(substring, from_undo=from_undo)


class CampoOraciones(CampoOrtografico):
    """CampoOrtografico que ademas pone en mayúscula la primera letra de
    cada oración (inicio del texto, o tras '.', '!', '?' o un salto de
    línea) a medida que se escribe. Se implementa sobre insert_text (el
    mismo mecanismo que usa Kivy para insertar cada tecla/IME), no
    reasignando self.text a mano (eso desincroniza self.cursor con la
    posición real del texto)."""

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


class CampoSimple(BorradoAcelerado, MDTextField):
    """MDTextField con borrado acelerado al mantener pulsado el retroceso
    (ver BorradoAcelerado) pero SIN corrección ortográfica -- para campos
    de valor corto donde el corrector estorba (correo, contraseña, servidor
    SMTP, responsable)."""


class BotonPlano(MDRaisedButton):
    """MDRaisedButton sin sombra. En esta versión de KivyMD la sombra de
    cualquier MDRaisedButton se dibuja SIEMPRE con esquinas cuadradas (la
    línea que la redondearía junto con `_radius` está comentada en el
    propio código fuente de KivyMD, y MDRaisedButton no tiene una
    propiedad `radius` real que la sombra pueda leer como respaldo) --
    detrás de un botón con esquinas redondeadas (`_radius: dp(14)`, único
    modo de redondear en esta versión, ver memoria de gotchas de KivyMD)
    esas esquinas cuadradas de la sombra asoman como un rectángulo oscuro
    semitransparente detrás del botón. Apagar la elevación evita dibujar
    la sombra por completo. No alcanza con pasar `elevation=0` al
    constructor: `ButtonElevationBehaviour.__init__` lo resetea a 2 si
    llega en 0 -- hay que asignarlo DESPUES de `super().__init__()`."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.elevation = 0
