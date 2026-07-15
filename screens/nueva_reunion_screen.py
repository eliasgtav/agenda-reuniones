# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
from kivy.lang import Builder
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.selectioncontrol import MDSwitch
from kivymd.uix.pickers import MDDatePicker, MDTimePicker

Builder.load_string('''
<NuevaReunionScreen>:
    MDScrollView:
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

                MDTextField:
                    id: asunto_field
                    hint_text: "Asunto de la reunión *"
                    helper_text: "Campo obligatorio"
                    helper_text_mode: "on_error"
                    mode: "rectangle"
                    font_size: '15sp'
                    on_text: self.text = self.text.upper()

                MDIconButton:
                    icon: "pencil"
                    size_hint_x: None
                    width: '36dp'
                    on_release: root.enfocar('asunto_field')

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

                MDTextField:
                    id: lugar_field
                    hint_text: "Lugar"
                    mode: "rectangle"
                    font_size: '15sp'
                    on_text: self.text = self.text.upper()

                MDIconButton:
                    icon: "pencil"
                    size_hint_x: None
                    width: '36dp'
                    on_release: root.enfocar('lugar_field')

            MDLabel:
                text: "Participantes"
                font_style: "Subtitle1"
                adaptive_height: True

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDTextField:
                    id: nuevo_participante
                    hint_text: "Nombre del participante"
                    mode: "rectangle"
                    font_size: '15sp'
                    size_hint_x: .75
                    on_text: self.text = self.text.upper()

                MDIconButton:
                    icon: "pencil"
                    size_hint_x: None
                    width: '36dp'
                    on_release: root.enfocar('nuevo_participante')

                MDIconButton:
                    icon: "account-plus"
                    on_release: root.agregar_participante_ui()

                MDIconButton:
                    icon: "contacts"
                    on_release: root.elegir_contacto()

            MDBoxLayout:
                id: participantes_list
                orientation: 'vertical'
                adaptive_height: True
                spacing: '4dp'

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

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDLabel:
                    text: "Notas adicionales"
                    font_style: "Subtitle1"
                    adaptive_height: True

                MDIconButton:
                    icon: "pencil"
                    size_hint_x: None
                    width: '36dp'
                    on_release: root.enfocar('notas_field')

            MDTextField:
                id: notas_field
                hint_text: "Escribe las notas con lápiz o teclado..."
                mode: "rectangle"
                multiline: True
                size_hint_y: None
                height: '180dp'
                font_size: '15sp'

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
    row = MDBoxLayout(adaptive_height=True, spacing=dp(4))
    row.add_widget(MDLabel(
        text=f'• {nombre}',
        adaptive_height=True,
        font_style='Body2',
    ))
    btn = MDIconButton(icon='close', size_hint_x=None, width=dp(36))
    btn.bind(on_release=on_remove)
    row.add_widget(btn)
    return row


class NuevaReunionScreen(MDScreen):
    _participantes = []
    _editar_id = None

    def on_pre_enter(self):
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self._reset_form(), 0)

    def enfocar(self, field_id):
        self.ids[field_id].focus = True

    def _reset_form(self):
        self._participantes = []
        self._editar_id = None
        self.ids.asunto_field.text = ''
        self.ids.fecha_field.text = ''
        self.ids.hora_field.text = ''
        self.ids.lugar_field.text = ''
        self.ids.notas_field.text = ''
        self.ids.nuevo_participante.text = ''
        self.ids.participantes_list.clear_widgets()

    def cargar_para_editar(self, reunion_id):
        app = App.get_running_app()
        r = app.db.obtener_reunion(reunion_id)
        if not r:
            return
        self._editar_id = reunion_id
        self.ids.asunto_field.text = r['asunto']
        self.ids.fecha_field.text = r['fecha']
        self.ids.hora_field.text = r['hora']
        self.ids.lugar_field.text = r['lugar'] or ''
        self.ids.notas_field.text = r['notas'] or ''
        self._participantes = [p['nombre'] for p in app.db.listar_participantes(reunion_id)]
        self._refrescar_participantes()

    def abrir_fecha(self):
        picker = MDDatePicker()
        picker.bind(on_save=self._on_fecha)
        picker.open()

    def _on_fecha(self, instance, value, *args):
        self.ids.fecha_field.text = value.strftime('%Y-%m-%d')

    def abrir_hora(self):
        picker = MDTimePicker()
        picker.bind(on_save=self._on_hora)
        picker.open()
        Clock.schedule_once(lambda dt: picker._switch_input(), 0.3)

    def _on_hora(self, instance, value):
        self.ids.hora_field.text = value.strftime('%H:%M')

    def agregar_participante_ui(self):
        nombre = self.ids.nuevo_participante.text.strip()
        if nombre and nombre not in self._participantes:
            self._participantes.append(nombre)
            self.ids.nuevo_participante.text = ''
            self._refrescar_participantes()

    def elegir_contacto(self):
        from utils.contactos import abrir_selector
        abrir_selector(self._contacto_elegido, self._mostrar_error)

    def _contacto_elegido(self, nombre):
        nombre = nombre.strip().upper()
        if nombre and nombre not in self._participantes:
            self._participantes.append(nombre)
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

        fecha = self.ids.fecha_field.text.strip()
        if not fecha:
            self._mostrar_error('Selecciona una fecha para la reunión.')
            return

        hora = self.ids.hora_field.text.strip() or '09:00'
        lugar = self.ids.lugar_field.text.strip()
        notas = self.ids.notas_field.text.strip()

        alertas = []
        if self.ids.sw_30min.active:
            alertas.append('30min')
        if self.ids.sw_1hora.active:
            alertas.append('1hora')
        if self.ids.sw_1dia.active:
            alertas.append('1dia')

        app = App.get_running_app()
        db = app.db

        if self._editar_id:
            db.actualizar_reunion(
                self._editar_id,
                asunto=asunto, fecha=fecha, hora=hora, lugar=lugar, notas=notas
            )
            for p in db.listar_participantes(self._editar_id):
                db.eliminar_participante(p['id'])
            for nombre in self._participantes:
                db.agregar_participante(self._editar_id, nombre)
        else:
            rid = db.crear_reunion(asunto, fecha, hora, lugar, notas, alertas)
            for nombre in self._participantes:
                db.agregar_participante(rid, nombre)

        self._mostrar_ok()

    def _mostrar_error(self, texto):
        dialog = MDDialog(
            title='Error',
            text=texto,
            buttons=[MDFlatButton(text='ACEPTAR', on_release=lambda x: dialog.dismiss())],
        )
        dialog.open()

    def _mostrar_ok(self):
        dialog = MDDialog(
            title='Reunión guardada',
            text='La reunión fue registrada exitosamente.',
            buttons=[
                MDFlatButton(
                    text='ACEPTAR',
                    on_release=lambda x: (dialog.dismiss(), App.get_running_app().go_to('dashboard')),
                )
            ],
        )
        dialog.open()
