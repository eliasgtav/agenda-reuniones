# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
from kivy.lang import Builder
from kivy.app import App
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from utils.config import cargar, guardar
from utils.voz import DictadoVoz

Builder.load_string('''
<LoginScreen>:
    MDBoxLayout:
        orientation: 'vertical'
        padding: '32dp'
        spacing: '20dp'
        md_bg_color: app.theme_cls.bg_normal

        MDBoxLayout:
            size_hint_y: None
            height: '40dp'

        MDLabel:
            text: "Agenda de Reuniones"
            font_style: "H4"
            halign: "center"
            adaptive_height: True
            theme_text_color: "Primary"

        MDLabel:
            text: "Bienvenido"
            font_style: "H6"
            halign: "center"
            adaptive_height: True
            theme_text_color: "Secondary"

        MDLabel:
            text: "Para comenzar, ingresa tu nombre completo"
            font_style: "Body1"
            halign: "center"
            adaptive_height: True
            theme_text_color: "Secondary"

        MDBoxLayout:
            size_hint_y: None
            height: '20dp'

        MDBoxLayout:
            adaptive_height: True
            spacing: '8dp'

            MDTextField:
                id: nombres_field
                hint_text: "Nombres *"
                mode: "rectangle"
                font_size: '15sp'
                on_text: self.text = self.text.upper()

            MDIconButton:
                icon: "pencil"
                size_hint_x: None
                width: '36dp'
                on_release: root.enfocar('nombres_field')

            MDIconButton:
                id: nombres_mic
                icon: "microphone"
                size_hint_x: None
                width: '36dp'
                theme_icon_color: "Custom"
                icon_color: 0.13, 0.40, 0.75, 1
                on_release: root.toggle_voz('nombres_field', 'nombres_mic')

        MDBoxLayout:
            adaptive_height: True
            spacing: '8dp'

            MDTextField:
                id: apellidos_field
                hint_text: "Apellidos *"
                mode: "rectangle"
                font_size: '15sp'
                on_text: self.text = self.text.upper()

            MDIconButton:
                icon: "pencil"
                size_hint_x: None
                width: '36dp'
                on_release: root.enfocar('apellidos_field')

            MDIconButton:
                id: apellidos_mic
                icon: "microphone"
                size_hint_x: None
                width: '36dp'
                theme_icon_color: "Custom"
                icon_color: 0.13, 0.40, 0.75, 1
                on_release: root.toggle_voz('apellidos_field', 'apellidos_mic')

        MDLabel:
            id: lbl_voz_estado
            text: ""
            font_style: "Caption"
            halign: "center"
            adaptive_height: True
            theme_text_color: "Custom"
            text_color: 0.13, 0.55, 0.13, 1

        MDBoxLayout:
            size_hint_y: None
            height: '16dp'

        MDRaisedButton:
            text: "INGRESAR A LA APP"
            pos_hint: {"center_x": .5}
            md_bg_color: 0.13, 0.40, 0.75, 1
            size_hint_x: .9
            height: '48dp'
            on_release: root.ingresar()

        MDBoxLayout:
            size_hint_y: None
            height: '30dp'

        MDLabel:
            text: "© Elías Gaytan Alvino"
            font_style: "Caption"
            halign: "center"
            adaptive_height: True
            theme_text_color: "Hint"
''')


class LoginScreen(MDScreen):
    _dictados = None

    def enfocar(self, field_id):
        self.ids[field_id].focus = True

    def toggle_voz(self, campo_id, boton_id):
        if self._dictados is None:
            self._dictados = {}
        if campo_id not in self._dictados:
            self._dictados[campo_id] = DictadoVoz(
                campo=self.ids[campo_id],
                boton_mic=self.ids[boton_id],
                lbl_estado=self.ids.lbl_voz_estado,
                on_permiso_denegado=lambda texto: self._mostrar('Error', texto),
            )
        self._dictados[campo_id].toggle()

    def ingresar(self):
        nombres = self.ids.nombres_field.text.strip()
        apellidos = self.ids.apellidos_field.text.strip()

        if not nombres:
            self._mostrar('Error', 'Por favor ingresa tus nombres.')
            return
        if not apellidos:
            self._mostrar('Error', 'Por favor ingresa tus apellidos.')
            return

        nombre_completo = f'{nombres} {apellidos}'
        config = cargar()
        config['nombres'] = nombres
        config['apellidos'] = apellidos
        config['nombre'] = nombre_completo
        config['registrado'] = True
        guardar(config)

        App.get_running_app().go_to('dashboard')

    def _mostrar(self, titulo, texto):
        dialog = MDDialog(
            title=titulo,
            text=texto,
            buttons=[MDFlatButton(text='OK', on_release=lambda x: dialog.dismiss())],
        )
        dialog.open()
