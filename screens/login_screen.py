# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.app import App
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from utils.config import cargar, guardar
from utils.widgets import CampoMayusculas, BotonPlano

Builder.load_string('''
<LoginScreen>:
    MDScrollView:
        MDBoxLayout:
            orientation: 'vertical'
            padding: '32dp'
            spacing: '20dp'
            adaptive_height: True
            md_bg_color: app.theme_cls.bg_normal

            MDBoxLayout:
                size_hint_y: None
                height: '24dp'

            # Círculo con iniciales en vivo, mismo lenguaje visual que Mi Perfil
            AnchorLayout:
                size_hint_y: None
                height: '110dp'
                anchor_x: 'center'
                anchor_y: 'center'

                MDCard:
                    size_hint: None, None
                    size: '100dp', '100dp'
                    radius: [dp(50)]
                    elevation: 4
                    md_bg_color: app.theme_cls.primary_color

                    MDLabel:
                        id: iniciales_lbl
                        text: ""
                        font_style: "H4"
                        halign: "center"
                        valign: "middle"
                        theme_text_color: "Custom"
                        text_color: 1, 1, 1, 1
                        text_size: self.size

            MDLabel:
                text: "Agenda de Reuniones"
                font_style: "H5"
                halign: "center"
                adaptive_height: True
                theme_text_color: "Primary"

            MDLabel:
                text: "Ingresa tu nombre para comenzar"
                font_style: "Body1"
                halign: "center"
                adaptive_height: True
                theme_text_color: "Secondary"

            MDBoxLayout:
                size_hint_y: None
                height: '10dp'

            CampoMayusculas:
                id: nombres_field
                hint_text: "Nombres *"
                mode: "rectangle"
                size_hint_x: 0.75
                pos_hint: {"center_x": .5}
                on_text: root._actualizar_iniciales()

            CampoMayusculas:
                id: apellidos_field
                hint_text: "Apellidos *"
                mode: "rectangle"
                size_hint_x: 0.75
                pos_hint: {"center_x": .5}
                on_text: root._actualizar_iniciales()

            MDBoxLayout:
                size_hint_y: None
                height: '10dp'

            BotonPlano:
                text: "INGRESAR A LA APP"
                pos_hint: {"center_x": .5}
                size_hint_x: None
                width: dp(220)
                _radius: dp(14)
                md_bg_color: 0.13, 0.40, 0.75, 1
                on_release: root.ingresar()

            MDBoxLayout:
                size_hint_y: None
                height: '20dp'

            MDLabel:
                text: "© Elías Gaytan Alvino"
                font_style: "Caption"
                halign: "center"
                adaptive_height: True
                theme_text_color: "Hint"
''')


class LoginScreen(MDScreen):

    def _actualizar_iniciales(self):
        nombres = self.ids.nombres_field.text.strip()
        apellidos = self.ids.apellidos_field.text.strip()
        self.ids.iniciales_lbl.text = (nombres[:1] + apellidos[:1]).upper()

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
