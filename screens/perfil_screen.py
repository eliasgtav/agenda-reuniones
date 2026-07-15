# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
import os
import shutil
from kivy.lang import Builder
from kivy.app import App
from kivy.metrics import dp
from kivy.utils import platform
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from utils.config import cargar, guardar

Builder.load_string('''
<PerfilScreen>:
    MDScrollView:
        MDBoxLayout:
            orientation: 'vertical'
            padding: '24dp'
            spacing: '20dp'
            adaptive_height: True

            MDLabel:
                text: "Mi Perfil"
                font_style: "H5"
                halign: "center"
                adaptive_height: True

            # Foto circular centrada
            AnchorLayout:
                size_hint_y: None
                height: '160dp'
                anchor_x: 'center'
                anchor_y: 'center'

                MDCard:
                    id: foto_card
                    size_hint: None, None
                    size: '140dp', '140dp'
                    radius: [70]
                    elevation: 4
                    md_bg_color: .85, .85, .85, 1
                    ripple_behavior: True
                    on_release: root.seleccionar_foto()

                    Image:
                        id: foto_img
                        source: ""
                        allow_stretch: True
                        keep_ratio: False
                        size_hint: 1, 1

            MDLabel:
                text: "Toca la foto para cambiarla"
                font_style: "Caption"
                halign: "center"
                adaptive_height: True
                theme_text_color: "Secondary"

            MDTextField:
                id: nombres_field
                hint_text: "Nombres *"
                mode: "rectangle"
                icon_right: "account"
                on_text: self.text = self.text.upper()

            MDTextField:
                id: apellidos_field
                hint_text: "Apellidos *"
                mode: "rectangle"
                icon_right: "account"
                on_text: self.text = self.text.upper()

            MDRaisedButton:
                text: "CAMBIAR FOTO"
                pos_hint: {"center_x": .5}
                md_bg_color: 0.40, 0.23, 0.72, 1
                on_release: root.seleccionar_foto()

            MDRaisedButton:
                text: "GUARDAR PERFIL"
                pos_hint: {"center_x": .5}
                md_bg_color: 0.13, 0.40, 0.75, 1
                on_release: root.guardar_perfil()

            # ── Configuración de correo ───────────────────────────────
            MDLabel:
                text: "Configuración de correo"
                font_style: "Subtitle1"
                adaptive_height: True

            MDLabel:
                text: "El acta se enviará al terminar cada reunión"
                font_style: "Caption"
                adaptive_height: True
                theme_text_color: "Secondary"

            MDTextField:
                id: correo_origen_field
                hint_text: "Tu correo (remitente)"
                mode: "rectangle"
                icon_right: "email"

            MDTextField:
                id: correo_password_field
                hint_text: "Contraseña de aplicación"
                mode: "rectangle"
                password: True
                icon_right: "lock"

            MDTextField:
                id: correo_destino_field
                hint_text: "Correo destinatario del acta"
                mode: "rectangle"
                icon_right: "email-send"

            MDTextField:
                id: smtp_server_field
                hint_text: "Servidor SMTP (ej: smtp.gmail.com)"
                mode: "rectangle"
                text: "smtp.gmail.com"

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDRaisedButton:
                    text: "GUARDAR CORREO"
                    md_bg_color: 0.13, 0.55, 0.13, 1
                    on_release: root.guardar_correo()

                MDRaisedButton:
                    text: "PROBAR ENVÍO"
                    md_bg_color: 0.40, 0.23, 0.72, 1
                    on_release: root.probar_correo()

            MDLabel:
                text: "Para Gmail: activa verificación en 2 pasos y genera una 'Contraseña de aplicación' en tu cuenta Google."
                font_style: "Caption"
                adaptive_height: True
                theme_text_color: "Secondary"

            MDLabel:
                text: "Zona de peligro"
                font_style: "Subtitle1"
                adaptive_height: True
                theme_text_color: "Custom"
                text_color: 0.8, 0.1, 0.1, 1

            MDRaisedButton:
                text: "ELIMINAR TODAS LAS REUNIONES"
                pos_hint: {"center_x": .5}
                md_bg_color: 0.8, 0.1, 0.1, 1
                on_release: root.confirmar_borrar_bd()

            MDFlatButton:
                text: "VOLVER"
                pos_hint: {"center_x": .5}
                on_release: app.go_back()

            MDLabel:
                text: "© Elías Gaytan Alvino"
                font_style: "Caption"
                halign: "center"
                adaptive_height: True
                padding: [0, "16dp"]
''')

class PerfilScreen(MDScreen):
    def on_pre_enter(self):
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self._cargar_perfil(), 0)

    def _cargar_perfil(self):
        config = cargar()
        self.ids.nombres_field.text   = config.get('nombres', '')
        self.ids.apellidos_field.text = config.get('apellidos', '')
        foto = config.get('foto_perfil', '')
        self.ids.foto_img.source = foto if foto and os.path.exists(foto) else ''
        self.ids.correo_origen_field.text  = config.get('correo_origen', '')
        self.ids.correo_password_field.text = config.get('correo_password', '')
        self.ids.correo_destino_field.text  = config.get('correo_destino', '')
        self.ids.smtp_server_field.text     = config.get('smtp_server', 'smtp.gmail.com')

    def seleccionar_foto(self):
        try:
            from plyer import filechooser

            def _on_seleccion(seleccion):
                if not seleccion:
                    return
                ruta_orig = seleccion[0]
                ext = os.path.splitext(ruta_orig)[1].lower()
                if ext not in ('.jpg', '.jpeg', '.png', '.bmp', '.gif'):
                    self._mostrar('Error', 'Selecciona una imagen (JPG, PNG, BMP).')
                    return
                if platform == 'android':
                    from android.storage import app_storage_path
                    dest_dir = app_storage_path()
                else:
                    dest_dir = os.path.join(os.path.expanduser('~'), 'agenda_adjuntos')
                os.makedirs(dest_dir, exist_ok=True)
                dest = os.path.join(dest_dir, 'foto_perfil' + ext)
                shutil.copy2(ruta_orig, dest)
                self.ids.foto_img.source = ''
                self.ids.foto_img.source = dest
                config = cargar()
                config['foto_perfil'] = dest
                guardar(config)
                App.get_running_app().actualizar_foto_dashboard()

            filechooser.open_file(
                on_selection=_on_seleccion,
                filters=['*.jpg', '*.jpeg', '*.png', '*.bmp'],
            )
        except Exception as e:
            self._mostrar('Error', f'No se pudo abrir el selector: {e}')

    def guardar_correo(self):
        config = cargar()
        config['correo_origen']   = self.ids.correo_origen_field.text.strip()
        config['correo_password'] = self.ids.correo_password_field.text.strip()
        config['correo_destino']  = self.ids.correo_destino_field.text.strip()
        config['smtp_server']     = self.ids.smtp_server_field.text.strip() or 'smtp.gmail.com'
        config['smtp_port']       = 587
        guardar(config)
        self._mostrar('Correo guardado', 'Configuración guardada. Usa "PROBAR ENVÍO" para verificar.')

    def probar_correo(self):
        from utils.email_sender import probar_conexion
        from utils.config import cargar as cargar_config
        from kivy.clock import Clock
        self.guardar_correo()
        self._mostrar('Probando...', 'Enviando correo de prueba, espera unos segundos.')

        def _resultado(ok, msg):
            Clock.schedule_once(lambda dt: self._mostrar(
                '✓ Éxito' if ok else '⚠ Error', msg
            ), 0)

        probar_conexion(cargar_config(), callback=_resultado)

    def guardar_perfil(self):
        nombres   = self.ids.nombres_field.text.strip()
        apellidos = self.ids.apellidos_field.text.strip()
        if not nombres:
            self._mostrar('Error', 'Escribe tus nombres.')
            return
        if not apellidos:
            self._mostrar('Error', 'Escribe tus apellidos.')
            return
        config = cargar()
        config['nombres']   = nombres
        config['apellidos'] = apellidos
        config['nombre']    = f'{nombres} {apellidos}'
        guardar(config)
        App.get_running_app().actualizar_foto_dashboard()
        self._mostrar('Guardado', f'Perfil actualizado:\n{nombres} {apellidos}')

    def confirmar_borrar_bd(self):
        from kivymd.uix.button import MDRaisedButton
        dialog = MDDialog(
            title='¿Eliminar todas las reuniones?',
            text='Esta acción borrará permanentemente todas las reuniones, participantes y alertas. No se puede deshacer.',
            buttons=[
                MDFlatButton(text='CANCELAR', on_release=lambda x: dialog.dismiss()),
                MDRaisedButton(
                    text='ELIMINAR TODO',
                    md_bg_color=(0.8, 0.1, 0.1, 1),
                    on_release=lambda x: [dialog.dismiss(), self._borrar_bd()],
                ),
            ],
        )
        dialog.open()

    def _borrar_bd(self):
        app = App.get_running_app()
        with app.db._conn() as conn:
            conn.executescript('''
                DELETE FROM alertas;
                DELETE FROM archivos;
                DELETE FROM participantes;
                DELETE FROM reuniones;
            ''')
        self._mostrar('Listo', 'Todas las reuniones han sido eliminadas.')

    def _mostrar(self, titulo, texto):
        dialog = MDDialog(
            title=titulo,
            text=texto,
            buttons=[MDFlatButton(text='OK', on_release=lambda x: dialog.dismiss())],
        )
        dialog.open()
