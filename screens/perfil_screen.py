# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
import os
from kivy.lang import Builder
from kivy.app import App
from kivy.metrics import dp
from kivy.utils import platform
from kivy.cache import Cache
from kivy.uix.popup import Popup
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scatter import Scatter
from kivy.uix.stencilview import StencilView
from kivy.uix.image import Image as KivyImage
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from utils.config import cargar, guardar
from utils.voz import DictadoVoz

EXTENSIONES_FOTO = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
_EXTENSIONES_FOTO_TXT = 'JPG, JPEG, PNG, BMP o GIF'
_LADO_RECORTE = 480

Builder.load_string('''
<PerfilScreen>:
    MDScrollView:
        id: scroll_view
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
                    on_release: root.elegir_foto()

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

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDTextField:
                    id: nombres_field
                    hint_text: "Nombres *"
                    mode: "rectangle"
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

            MDRaisedButton:
                text: "CAMBIAR FOTO"
                pos_hint: {"center_x": .5}
                md_bg_color: 0.40, 0.23, 0.72, 1
                on_release: root.elegir_foto()

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
    _scroll_retry_events = None
    _load_event = None
    _dictados = None

    def on_pre_enter(self):
        from kivy.clock import Clock
        self._load_event = Clock.schedule_once(lambda dt: self._cargar_perfil(), 0)

    def on_leave(self):
        # Ver nota completa en dashboard_screen.py.
        if self._load_event:
            self._load_event.cancel()
            self._load_event = None
        for ev in (self._scroll_retry_events or []):
            ev.cancel()
        self._scroll_retry_events = None

    def _cargar_perfil(self):
        config = cargar()
        self.ids.nombres_field.text   = config.get('nombres', '')
        self.ids.apellidos_field.text = config.get('apellidos', '')
        self.ids.lbl_voz_estado.text  = ''
        foto = config.get('foto_perfil', '')
        self.ids.foto_img.source = foto if foto and os.path.exists(foto) else ''
        self.ids.correo_origen_field.text  = config.get('correo_origen', '')
        self.ids.correo_password_field.text = config.get('correo_password', '')
        self.ids.correo_destino_field.text  = config.get('correo_destino', '')
        self.ids.smtp_server_field.text     = config.get('smtp_server', 'smtp.gmail.com')
        self._forzar_scroll_arriba()

    def enfocar(self, field_id):
        self.ids[field_id].focus = True

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

    def _forzar_scroll_arriba(self):
        # Ver nota completa en dashboard_screen.py.
        from kivy.clock import Clock
        sv = self.ids.scroll_view

        def _reset(dt=None):
            sv.scroll_y = 1
            sv.update_from_scroll()

        _reset()
        self._scroll_retry_events = [
            Clock.schedule_once(_reset, delay)
            for delay in (0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0)
        ]

    def _rutas_foto(self):
        if platform == 'android':
            from android.storage import app_storage_path
            dest_dir = app_storage_path()
        else:
            dest_dir = os.path.join(os.path.expanduser('~'), 'agenda_adjuntos')
        os.makedirs(dest_dir, exist_ok=True)
        return dest_dir, os.path.join(dest_dir, 'foto_perfil.png')

    def elegir_foto(self):
        dialog = MDDialog(
            title='Foto de perfil',
            text='¿De dónde quieres tomar la foto?',
            buttons=[
                MDFlatButton(text='CANCELAR', on_release=lambda x: dialog.dismiss()),
                MDFlatButton(
                    text='GALERÍA',
                    on_release=lambda x: [dialog.dismiss(), self._desde_galeria()],
                ),
                MDRaisedButton(
                    text='CÁMARA',
                    md_bg_color=(0.13, 0.40, 0.75, 1),
                    on_release=lambda x: [dialog.dismiss(), self._desde_camara()],
                ),
            ],
        )
        dialog.open()

    def _desde_galeria(self):
        # plyer.filechooser en Android devuelve URIs content:// que PIL no
        # puede abrir directo, y en pruebas reales el selector no llegaba a
        # cargar la imagen -- en Android se usa un Intent nativo
        # (utils/foto_selector.py) que copia la imagen a un archivo local
        # de verdad antes de abrirla con PIL.
        if platform == 'android':
            from utils import foto_selector
            dest_dir, _dest = self._rutas_foto()
            foto_selector.abrir_galeria(dest_dir, self._on_foto_temporal, self._mostrar_error)
            return
        try:
            from plyer import filechooser

            def _on_seleccion(seleccion):
                if not seleccion:
                    return
                ruta_orig = seleccion[0]
                ext = os.path.splitext(ruta_orig)[1].lower()
                if ext not in EXTENSIONES_FOTO:
                    self._mostrar('Error', f'Selecciona una imagen ({_EXTENSIONES_FOTO_TXT}).')
                    return
                self._on_foto_temporal(ruta_orig)

            filechooser.open_file(
                on_selection=_on_seleccion,
                filters=[f'*{e}' for e in EXTENSIONES_FOTO],
            )
        except Exception as e:
            self._mostrar('Error', f'No se pudo abrir el selector: {e}')

    def _desde_camara(self):
        if platform != 'android':
            self._mostrar('Error', 'La cámara solo está disponible en el celular.')
            return
        from utils import foto_selector
        dest_dir, _dest = self._rutas_foto()
        foto_selector.abrir_camara(dest_dir, self._on_foto_temporal, self._mostrar_error)

    def _on_foto_temporal(self, ruta_temp):
        dest_dir, dest = self._rutas_foto()
        try:
            from PIL import Image, ImageOps
            img = ImageOps.exif_transpose(Image.open(ruta_temp)).convert('RGB')
            tmp = os.path.join(dest_dir, '_recorte_temp.png')
            img.save(tmp, format='PNG')
            img_w, img_h = img.size
        except Exception as e:
            self._mostrar('Error', f'No se pudo abrir la imagen: {e}')
            return
        self._abrir_recorte(tmp, img_w, img_h, dest)

    def _mostrar_error(self, texto):
        self._mostrar('Error', texto)

    def _abrir_recorte(self, ruta_temp, img_w, img_h, dest):
        """Popup con arrastre/zoom (Scatter + StencilView) para elegir qué
        área cuadrada de la foto elegida se usa, antes de recortarla a
        _LADO_RECORTE x _LADO_RECORTE y guardarla en `dest`."""
        marco = dp(280)
        escala_min = marco / min(img_w, img_h)

        stencil = StencilView(size=(marco, marco), size_hint=(None, None), pos=(0, 0))
        scatter = Scatter(
            size=(img_w, img_h), size_hint=(None, None),
            do_rotation=False, do_scale=True, do_translation=True,
            scale=escala_min, scale_min=escala_min, scale_max=escala_min * 5,
        )
        scatter.pos = (
            (marco - img_w * escala_min) / 2,
            (marco - img_h * escala_min) / 2,
        )
        scatter.add_widget(KivyImage(
            source=ruta_temp, size=(img_w, img_h), pos=(0, 0),
            allow_stretch=True, keep_ratio=False,
        ))
        stencil.add_widget(scatter)

        def _limitar(*_a):
            if scatter.scale < escala_min:
                scatter.scale = escala_min
            w = img_w * scatter.scale
            h = img_h * scatter.scale
            x, y = scatter.pos
            if x > 0:
                x = 0
            if x + w < marco:
                x = marco - w
            if y > 0:
                y = 0
            if y + h < marco:
                y = marco - h
            scatter.pos = (x, y)

        scatter.bind(pos=_limitar, scale=_limitar)

        contenedor = AnchorLayout(size_hint_y=None, height=marco, anchor_x='center', anchor_y='center')
        contenedor.add_widget(stencil)

        raiz = MDBoxLayout(orientation='vertical', spacing=dp(12), padding=dp(16), adaptive_height=True)
        raiz.add_widget(MDLabel(
            text='Arrastra y pellizca para elegir el área de la foto',
            halign='center',
            adaptive_height=True,
            font_style='Caption',
        ))
        raiz.add_widget(contenedor)

        botones = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        btn_cancelar = MDFlatButton(text='CANCELAR')
        btn_confirmar = MDRaisedButton(text='RECORTAR Y GUARDAR', md_bg_color=(0.13, 0.40, 0.75, 1))
        botones.add_widget(btn_cancelar)
        botones.add_widget(btn_confirmar)
        raiz.add_widget(botones)

        popup = Popup(
            title='Recortar foto de perfil',
            content=raiz,
            size_hint=(0.92, None),
            height=marco + dp(180),
            auto_dismiss=False,
        )

        def _borrar_temp():
            try:
                os.remove(ruta_temp)
            except Exception:
                pass

        def _cancelar(*_a):
            popup.dismiss()
            _borrar_temp()

        def _confirmar(*_a):
            try:
                self._guardar_recorte(ruta_temp, img_w, img_h, scatter, marco, dest)
            except Exception as e:
                self._mostrar('Error', f'No se pudo guardar el recorte: {e}')
                return
            finally:
                _borrar_temp()
            popup.dismiss()

        btn_cancelar.bind(on_release=_cancelar)
        btn_confirmar.bind(on_release=_confirmar)
        popup.open()

    def _guardar_recorte(self, ruta_temp, img_w, img_h, scatter, marco, dest):
        from PIL import Image
        x, y = scatter.pos
        s = scatter.scale

        x0 = max(0.0, min(img_w, (0 - x) / s))
        x1 = max(0.0, min(img_w, (marco - x) / s))
        y0_local = (0 - y) / s
        y1_local = (marco - y) / s
        # Kivy mide Y de abajo hacia arriba; PIL de arriba hacia abajo.
        y0 = max(0.0, min(img_h, img_h - y1_local))
        y1 = max(0.0, min(img_h, img_h - y0_local))

        img = Image.open(ruta_temp).convert('RGB')
        img = img.crop((x0, y0, x1, y1))
        img = img.resize((_LADO_RECORTE, _LADO_RECORTE), Image.LANCZOS)
        img.save(dest, format='PNG')

        # foto_perfil.png es siempre el mismo nombre de archivo: Kivy cachea
        # imágenes por ruta (sin mirar la fecha de modificación), así que hay
        # que invalidar la cache o la app sigue mostrando la foto anterior.
        Cache.remove('kv.image')
        Cache.remove('kv.texture')

        self.ids.foto_img.source = ''
        self.ids.foto_img.source = dest
        config = cargar()
        config['foto_perfil'] = dest
        guardar(config)
        App.get_running_app().actualizar_foto_dashboard()

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
