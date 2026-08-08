# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Campo de texto que delega la corrección ortográfica y las sugerencias
al teclado nativo del sistema (Gboard, SwiftKey, etc.) en vez de una
barra flotante propia dentro del lienzo de la app -- así la barra de
sugerencias aparece pegada al teclado, igual que en WhatsApp/Notas."""
import re
from time import time

from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.textfield import MDTextField


class CampoOrtografico(MDTextField):
    """MDTextField que pide explícitamente input_type='text' (el default
    de Kivy 2.3 es 'null', que en Android corre el teclado en modo
    limitado "generate key events" y SUPRIME la barra nativa de
    sugerencias/autocorrección pase lo que sea keyboard_suggestions) y
    keyboard_suggestions=True, para que el propio teclado del sistema
    muestre su franja de sugerencias sin que la app tenga que dibujar
    nada encima."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.input_type = 'text'
        self.keyboard_suggestions = True
        self._ultimo_toque_ts = 0
        self._ultimo_toque_pos = None

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
