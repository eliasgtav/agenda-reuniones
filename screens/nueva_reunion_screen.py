# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
from datetime import datetime
from kivy.lang import Builder
from kivy.app import App
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.uix.behaviors import ButtonBehavior
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.selectioncontrol import MDSwitch
from utils.voz import DictadoVoz
from utils.widgets import CampoMayusculas
from utils.mixins_pantalla import ScrollArribaMixin
from utils.dialogos import abrir_selector_fecha, abrir_selector_hora, mostrar_info


class BotonQuitarParticipante(ButtonBehavior, MDIcon):
    """Icono 'x' compacto: a diferencia de MDIconButton, no fuerza 48dp."""


Builder.load_string('''
<ChipParticipante@MDBoxLayout>:
    adaptive_height: True
    spacing: '4dp'

    MDLabel:
        id: lbl_nombre
        adaptive_height: True
        font_style: 'Body2'
        valign: 'center'

    BotonQuitarParticipante:
        id: btn_quitar
        icon: 'delete'
        size_hint: None, None
        size: '20dp', '20dp'

<NuevaReunionScreen>:
    MDScrollView:
        id: scroll_view
        MDBoxLayout:
            orientation: 'vertical'
            padding: '16dp'
            spacing: '10dp'
            adaptive_height: True

            MDLabel:
                text: "Nueva Reunión"
                font_style: "H5"
                adaptive_height: True

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                CampoMayusculas:
                    id: asunto_field
                    hint_text: "Asunto de la reunión *"
                    mode: "rectangle"
                    font_size: '15sp'

                MDBoxLayout:
                    adaptive_size: True
                    spacing: '0dp'

                    MDIconButton:
                        icon: "pencil"
                        size_hint: None, None
                        size: '32dp', '32dp'
                        on_release: root.enfocar('asunto_field')

                    MDIconButton:
                        id: asunto_mic
                        icon: "microphone"
                        size_hint: None, None
                        size: '32dp', '32dp'
                        theme_icon_color: "Custom"
                        icon_color: 0.13, 0.40, 0.75, 1
                        on_release: root.toggle_voz('asunto_field', 'asunto_mic')

                    MDIconButton:
                        icon: "eraser"
                        size_hint: None, None
                        size: '32dp', '32dp'
                        on_press: root.borrar_seleccion('asunto_field')

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDTextField:
                    id: fecha_field
                    hint_text: "Fecha *"
                    mode: "rectangle"
                    readonly: True
                    on_focus: if self.focus: root.abrir_fecha()

                MDIconButton:
                    icon: "calendar"
                    size_hint_x: None
                    width: '36dp'
                    on_release: root.abrir_fecha()

                MDTextField:
                    id: hora_field
                    hint_text: "Hora"
                    mode: "rectangle"
                    readonly: True
                    on_focus: if self.focus: root.abrir_hora()

                MDIconButton:
                    icon: "clock-outline"
                    size_hint_x: None
                    width: '36dp'
                    on_release: root.abrir_hora()

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                CampoMayusculas:
                    id: lugar_field
                    hint_text: "Lugar"
                    mode: "rectangle"
                    font_size: '15sp'

                MDBoxLayout:
                    adaptive_size: True
                    spacing: '0dp'

                    MDIconButton:
                        icon: "pencil"
                        size_hint: None, None
                        size: '32dp', '32dp'
                        on_release: root.enfocar('lugar_field')

                    MDIconButton:
                        id: lugar_mic
                        icon: "microphone"
                        size_hint: None, None
                        size: '32dp', '32dp'
                        theme_icon_color: "Custom"
                        icon_color: 0.13, 0.40, 0.75, 1
                        on_release: root.toggle_voz('lugar_field', 'lugar_mic')

                    MDIconButton:
                        icon: "eraser"
                        size_hint: None, None
                        size: '32dp', '32dp'
                        on_press: root.borrar_seleccion('lugar_field')

            MDLabel:
                text: "Modalidad"
                font_style: "Subtitle1"
                adaptive_height: True

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDRaisedButton:
                    id: btn_presencial
                    text: "PRESENCIAL"
                    size_hint_x: 1
                    on_release: root.elegir_modalidad('presencial')

                MDRaisedButton:
                    id: btn_virtual
                    text: "VIRTUAL"
                    size_hint_x: 1
                    on_release: root.elegir_modalidad('virtual')

            MDLabel:
                text: "Participantes"
                font_style: "Subtitle1"
                adaptive_height: True

            MDBoxLayout:
                adaptive_height: True
                spacing: '4dp'

                CampoMayusculas:
                    id: nuevo_participante
                    hint_text: "Nombre del participante"
                    mode: "rectangle"
                    font_size: '15sp'
                    size_hint_x: 1

                MDBoxLayout:
                    adaptive_size: True
                    spacing: '0dp'

                    MDIconButton:
                        id: participante_mic
                        icon: "microphone"
                        size_hint: None, None
                        size: '28dp', '28dp'
                        theme_icon_color: "Custom"
                        icon_color: 0.13, 0.40, 0.75, 1
                        on_release: root.toggle_voz('nuevo_participante', 'participante_mic')

                    MDIconButton:
                        icon: "eraser"
                        size_hint: None, None
                        size: '28dp', '28dp'
                        on_press: root.borrar_seleccion('nuevo_participante')

                    MDIconButton:
                        icon: "account-plus"
                        size_hint: None, None
                        size: '28dp', '28dp'
                        on_release: root.agregar_participante_ui()

            MDBoxLayout:
                id: participantes_list
                orientation: 'vertical'
                adaptive_height: True
                spacing: '0dp'
                padding: '12dp', '0dp', '0dp', '0dp'

            MDLabel:
                text: "Alertas de recordatorio"
                font_style: "Subtitle1"
                adaptive_height: True

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDSwitch:
                    id: sw_30min
                    active: True
                MDLabel:
                    text: "10 min antes"
                    adaptive_height: True
                    valign: "center"

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDSwitch:
                    id: sw_1hora
                    active: True
                MDLabel:
                    text: "15 min antes"
                    adaptive_height: True
                    valign: "center"

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDSwitch:
                    id: sw_1dia
                    active: True
                MDLabel:
                    text: "30 min antes"
                    adaptive_height: True
                    valign: "center"

            MDLabel:
                id: lbl_voz_estado
                text: ""
                font_style: "Caption"
                halign: "center"
                adaptive_height: True
                theme_text_color: "Custom"
                text_color: 0.13, 0.55, 0.13, 1

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDFlatButton:
                    text: "CANCELAR"
                    on_release: app.go_back()

                MDRaisedButton:
                    text: "GUARDAR REUNIÓN"
                    on_release: root.guardar()
''')


def _chip_participante(nombre, on_remove):
    row = Factory.ChipParticipante()
    row.ids.lbl_nombre.text = f'• {nombre}'
    row.ids.btn_quitar.bind(on_release=on_remove)
    return row


class NuevaReunionScreen(ScrollArribaMixin, MDScreen):
    # None en vez de [] -- una lista literal como valor de clase es
    # compartida por TODAS las instancias (aqui inofensivo porque solo
    # existe una NuevaReunionScreen y _reset_form() la reemplaza por una
    # propia en cada entrada a la pantalla, pero es la misma trampa clasica
    # de Python que _dictados ya evita justo debajo).
    _participantes = None
    _dictados = None
    _load_event = None

    def on_pre_enter(self):
        from kivy.clock import Clock
        self._load_event = Clock.schedule_once(lambda dt: self._reset_form(), 0)

    def on_leave(self):
        if self._load_event:
            self._load_event.cancel()
            self._load_event = None
        self._cancelar_scroll_retries()

    def enfocar(self, field_id):
        self.ids[field_id].focus = True

    def borrar_seleccion(self, field_id):
        campo = self.ids[field_id]
        if campo.selection_text:
            campo.delete_selection()

    def _reset_form(self):
        self._participantes = []
        self.ids.asunto_field.text = ''
        self.ids.fecha_field.text = ''
        self.ids.hora_field.text = ''
        self.ids.lugar_field.text = ''
        self.ids.nuevo_participante.text = ''
        self.ids.lbl_voz_estado.text = ''
        self.ids.participantes_list.clear_widgets()
        self.elegir_modalidad('presencial')
        self._forzar_scroll_arriba()

    # ── Dictado por voz ──────────────────────────────────────────────

    def toggle_voz(self, campo_id, boton_id):
        if self._dictados is None:
            self._dictados = {}
        if campo_id not in self._dictados:
            self._dictados[campo_id] = DictadoVoz(
                campo=self.ids[campo_id],
                boton_mic=self.ids[boton_id],
                lbl_estado=self.ids.lbl_voz_estado,
                on_permiso_denegado=self._mostrar_error,
            )
        self._dictados[campo_id].toggle()

    # ── Modalidad ────────────────────────────────────────────────────

    _modalidad = 'presencial'

    def elegir_modalidad(self, valor):
        self._modalidad = valor
        seleccionado = (0.13, 0.40, 0.75, 1)
        no_seleccionado = (0.75, 0.75, 0.75, 1)
        self.ids.btn_presencial.md_bg_color = seleccionado if valor == 'presencial' else no_seleccionado
        self.ids.btn_virtual.md_bg_color = seleccionado if valor == 'virtual' else no_seleccionado

    def abrir_fecha(self):
        # fecha_field muestra DD/MM/AAAA (igual que el diálogo de "Nuevo
        # acuerdo con plazo") -- guardar() la convierte de vuelta a ISO al
        # crear la reunión.
        abrir_selector_fecha(lambda fecha_iso: setattr(
            self.ids.fecha_field, 'text', datetime.strptime(fecha_iso, '%Y-%m-%d').strftime('%d/%m/%Y')
        ))

    def abrir_hora(self):
        abrir_selector_hora(lambda texto: setattr(self.ids.hora_field, 'text', texto))

    def agregar_participante_ui(self):
        nombre = self.ids.nuevo_participante.text.strip()
        if nombre and nombre not in self._participantes:
            self._participantes.append(nombre)
            self.ids.nuevo_participante.text = ''
            self._refrescar_participantes()

    def _refrescar_participantes(self):
        lista = self.ids.participantes_list
        lista.clear_widgets()
        for nombre in self._participantes:
            n = nombre  # capture for lambda

            def _remove(_, name=n):
                self._participantes.remove(name)
                self._refrescar_participantes()

            lista.add_widget(_chip_participante(nombre, _remove))

    def guardar(self):
        asunto = self.ids.asunto_field.text.strip()
        if not asunto:
            self.ids.asunto_field.error = True
            return

        fecha_texto = self.ids.fecha_field.text.strip()
        if not fecha_texto:
            self._mostrar_error('Selecciona una fecha para la reunión.')
            return
        # fecha_field muestra DD/MM/AAAA (ver abrir_fecha) -- la BD guarda
        # fecha en ISO 'YYYY-MM-DD' (necesario para que comparaciones tipo
        # "plazo < hoy" y el ORDER BY por fecha funcionen bien en SQLite).
        fecha = datetime.strptime(fecha_texto, '%d/%m/%Y').strftime('%Y-%m-%d')

        hora = self.ids.hora_field.text.strip() or '09:00'
        lugar = self.ids.lugar_field.text.strip()

        alertas = []
        if self.ids.sw_30min.active:
            alertas.append('30min')
        if self.ids.sw_1hora.active:
            alertas.append('1hora')
        if self.ids.sw_1dia.active:
            alertas.append('1dia')

        app = App.get_running_app()
        db = app.db

        rid = db.crear_reunion(asunto, fecha, hora, lugar, tipos_alerta=alertas, modalidad=self._modalidad)
        for nombre in self._participantes:
            db.agregar_participante(rid, nombre)

        self._mostrar_ok()

    def _mostrar_error(self, texto):
        mostrar_info('Error', texto, boton='ACEPTAR')

    def _mostrar_ok(self):
        mostrar_info(
            'Reunión guardada',
            'La reunión fue registrada exitosamente.',
            boton='ACEPTAR',
            on_cerrar=lambda: App.get_running_app().go_to('dashboard'),
        )
