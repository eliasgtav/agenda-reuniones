# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
import threading
from datetime import datetime
from kivy.lang import Builder
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.card import MDCard

Builder.load_string('''
<EnReunionScreen>:
    MDBoxLayout:
        orientation: 'vertical'

        # Encabezado de reunión activa
        MDCard:
            size_hint_y: None
            height: '70dp'
            padding: '12dp'
            radius: [0]
            md_bg_color: 0.8, 0.1, 0.1, 1

            MDBoxLayout:
                orientation: 'vertical'

                MDLabel:
                    id: lbl_asunto_activo
                    text: ""
                    font_style: "Subtitle1"
                    theme_text_color: "Custom"
                    text_color: 1, 1, 1, 1
                    adaptive_height: True
                    shorten: True
                    shorten_from: "right"

                MDLabel:
                    id: lbl_hora_activa
                    text: ""
                    font_style: "Caption"
                    theme_text_color: "Custom"
                    text_color: 1, 1, 1, 0.85
                    adaptive_height: True

        # Barra de herramientas
        MDBoxLayout:
            size_hint_y: None
            height: '48dp'
            padding: ['8dp', '4dp']
            spacing: '4dp'
            md_bg_color: 0.95, 0.95, 0.95, 1

            MDLabel:
                text: "Acuerdos de la reunión"
                font_style: "Subtitle2"
                adaptive_height: True
                valign: "center"

            MDIconButton:
                icon: "pencil"
                on_release: root.enfocar_campo()

            MDIconButton:
                id: btn_mic
                icon: "microphone"
                theme_icon_color: "Custom"
                icon_color: 0.13, 0.40, 0.75, 1
                on_release: root.toggle_voz()

            MDIconButton:
                icon: "delete-sweep"
                theme_icon_color: "Custom"
                icon_color: 0.70, 0.10, 0.10, 1
                on_release: root.limpiar_campo()

        # Estado de voz
        MDLabel:
            id: lbl_estado_voz
            text: ""
            font_style: "Caption"
            halign: "center"
            size_hint_y: None
            height: '24dp'
            theme_text_color: "Custom"
            text_color: 0.13, 0.55, 0.13, 1

        # Campo de entrada
        MDTextField:
            id: entrada_field
            hint_text: "Escribe el acuerdo con lápiz, teclado o voz..."
            mode: "rectangle"
            multiline: True
            size_hint_y: None
            height: '160dp'
            font_size: '15sp'
            padding: ['8dp', '8dp']

        # Plazo de cumplimiento (opcional)
        MDBoxLayout:
            adaptive_height: True
            spacing: '8dp'
            padding: ['0dp', '0dp']

            MDTextField:
                id: plazo_field
                hint_text: "Plazo de cumplimiento (opcional)"
                mode: "rectangle"
                font_size: '14sp'
                size_hint_x: .75
                on_focus: if self.focus: root.abrir_plazo()

            MDIconButton:
                icon: "calendar"
                size_hint_x: None
                width: '48dp'
                on_release: root.abrir_plazo()

        # Botón agregar acuerdo
        MDRaisedButton:
            text: "+ AGREGAR ACUERDO"
            pos_hint: {"center_x": .5}
            md_bg_color: 0.13, 0.40, 0.75, 1
            size_hint_x: .95
            on_release: root.agregar_acuerdo()

        # Lista de acuerdos
        MDScrollView:
            MDBoxLayout:
                id: lista_acuerdos
                orientation: 'vertical'
                adaptive_height: True
                padding: '8dp'
                spacing: '6dp'

        # Botones inferiores
        MDBoxLayout:
            size_hint_y: None
            height: '52dp'
            padding: ['8dp', '4dp']
            spacing: '8dp'

            MDRaisedButton:
                text: "GUARDAR EN NOTAS"
                md_bg_color: 0.13, 0.55, 0.13, 1
                on_release: root.guardar_en_notas()

            MDFlatButton:
                text: "VOLVER"
                on_release: app.go_back()
''')


class EnReunionScreen(MDScreen):
    _reunion_id = None
    _acuerdos = []
    _escuchando = False

    def on_pre_enter(self):
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self._cargar(), 0)

    def _cargar(self):
        app = App.get_running_app()
        self._reunion_id = getattr(app, 'reunion_activa_id', None)
        self._acuerdos = []
        self.ids.lista_acuerdos.clear_widgets()
        self.ids.entrada_field.text = ''
        self.ids.plazo_field.text = ''
        self.ids.lbl_estado_voz.text = ''

        if self._reunion_id:
            r = app.db.obtener_reunion(self._reunion_id)
            if r:
                self.ids.lbl_asunto_activo.text = r['asunto']
                self.ids.lbl_hora_activa.text = f"{r['fecha']}  {r['hora']}  —  {r['lugar'] or 'Sin lugar'}"
                # Cargar acuerdos previos desde notas si hay
                notas = r.get('notas', '')
                if '=== ACUERDOS ===' in notas:
                    bloque = notas.split('=== ACUERDOS ===')[-1].strip()
                    for linea in bloque.split('\n'):
                        linea = linea.strip()
                        if linea.startswith('•'):
                            self._acuerdos.append({'texto': linea[1:].strip(), 'plazo': ''})
                self._refrescar_lista()

    def enfocar_campo(self):
        self.ids.entrada_field.focus = True

    def limpiar_campo(self):
        self.ids.entrada_field.text = ''
        self.ids.lbl_estado_voz.text = ''

    def abrir_plazo(self):
        from kivymd.uix.pickers import MDDatePicker
        picker = MDDatePicker()
        picker.bind(on_save=self._on_plazo)
        picker.open()

    def _on_plazo(self, instance, value, *args):
        self.ids.plazo_field.text = value.strftime('%Y-%m-%d')

    def agregar_acuerdo(self):
        texto = self.ids.entrada_field.text.strip()
        if not texto:
            return
        plazo = self.ids.plazo_field.text.strip()
        ts = datetime.now().strftime('%H:%M')
        plazo_label = f' — plazo: {plazo}' if plazo else ''
        acuerdo = f'[{ts}] {texto}{plazo_label}'
        self._acuerdos.append({'texto': acuerdo, 'plazo': plazo})
        self.ids.entrada_field.text = ''
        self.ids.plazo_field.text = ''
        self.ids.lbl_estado_voz.text = ''
        self._refrescar_lista()

    def _refrescar_lista(self):
        lista = self.ids.lista_acuerdos
        lista.clear_widgets()
        for i, acuerdo in enumerate(self._acuerdos):
            texto_display = acuerdo['texto'] if isinstance(acuerdo, dict) else acuerdo
            card = MDCard(
                orientation='horizontal',
                padding=dp(10),
                size_hint_y=None,
                height=dp(60),
                radius=[8],
                md_bg_color=(0.94, 0.97, 1.0, 1),
            )
            lbl = MDLabel(
                text=f'• {texto_display}',
                font_style='Body2',
                adaptive_height=True,
            )
            idx = i
            btn_del = MDIconButton(
                icon='close',
                size_hint_x=None,
                width=dp(36),
            )
            btn_del.bind(on_release=lambda _, i=idx: self._borrar_acuerdo(i))
            card.add_widget(lbl)
            card.add_widget(btn_del)
            lista.add_widget(card)

        if not self._acuerdos:
            lista.add_widget(MDLabel(
                text='Aún no hay acuerdos registrados.',
                halign='center',
                font_style='Body2',
                adaptive_height=True,
                theme_text_color='Secondary',
            ))

    def _borrar_acuerdo(self, idx):
        if 0 <= idx < len(self._acuerdos):
            del self._acuerdos[idx]
            self._refrescar_lista()

    def guardar_en_notas(self):
        if not self._acuerdos:
            self._mostrar('Aviso', 'No hay acuerdos para guardar.')
            return
        app = App.get_running_app()
        r = app.db.obtener_reunion(self._reunion_id)
        notas_prev = r.get('notas', '') or ''
        if '=== ACUERDOS ===' in notas_prev:
            notas_prev = notas_prev.split('=== ACUERDOS ===')[0].rstrip()
        textos = []
        for a in self._acuerdos:
            if isinstance(a, dict):
                textos.append(a['texto'])
                if a.get('plazo'):
                    app.db.guardar_acuerdo(self._reunion_id, a['texto'], a['plazo'])
            else:
                textos.append(a)
        bloque = '\n\n=== ACUERDOS ===\n' + '\n'.join(f'• {t}' for t in textos)
        nuevas_notas = (notas_prev + bloque).strip()
        app.db.actualizar_reunion(self._reunion_id, notas=nuevas_notas)
        self._mostrar('Guardado', f'{len(self._acuerdos)} acuerdo(s) guardados en las notas de la reunión.')

    # ── Voz ──────────────────────────────────────────────────────────

    def toggle_voz(self):
        if self._escuchando:
            return
        self._escuchando = True
        self.ids.btn_mic.icon_color = (0.8, 0.1, 0.1, 1)
        self.ids.lbl_estado_voz.text = '🎤 Escuchando... habla ahora'
        if platform == 'android':
            # speech_recognition + PyAudio son librerias de escritorio, no
            # estan en buildozer.spec (PyAudio/portaudio no compila bien
            # para Android). En el telefono se usa la API nativa de Android
            # via plyer.stt.
            self._escuchar_voz_android()
        else:
            threading.Thread(target=self._escuchar_voz, daemon=True).start()

    def _escuchar_voz_android(self):
        try:
            from plyer import stt
            if not stt.exist():
                self._voz_error('Este dispositivo no tiene reconocimiento de voz disponible.')
                return
            stt._language = 'es-ES'  # el setter publico de plyer solo acepta en-US/pl-PL
            stt.prefer_offline = False
            stt.start()
            Clock.schedule_interval(self._revisar_stt_android, 0.3)
        except Exception as e:
            self._voz_error(f'Error: {e}')

    def _revisar_stt_android(self, dt):
        from plyer import stt
        if stt.listening:
            return
        Clock.unschedule(self._revisar_stt_android)
        if stt.errors:
            err = stt.errors[-1]
            stt.errors = []
            if 'no_match' in err or 'speech_timeout' in err:
                self._voz_error('No se detectó voz. Intenta de nuevo.')
            else:
                self._voz_error(f'Error: {err}')
            return
        if stt.results:
            texto = stt.results[0]
            stt.results = []
            self._insertar_voz(texto)
        else:
            self._voz_error('No se detectó voz.')

    def _escuchar_voz(self):
        from kivy.clock import Clock
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            r.pause_threshold = 1.5
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=10, phrase_time_limit=60)
            texto = r.recognize_google(audio, language='es-ES')
            Clock.schedule_once(lambda dt: self._insertar_voz(texto), 0)
        except Exception as e:
            msg = {
                'WaitTimeoutError': 'Tiempo agotado. No se detectó voz.',
                'UnknownValueError': 'No se entendió. Intenta de nuevo.',
                'RequestError': 'Sin conexión a internet.',
            }.get(type(e).__name__, f'Error: {e}')
            Clock.schedule_once(lambda dt: self._voz_error(msg), 0)

    def _insertar_voz(self, texto):
        actual = self.ids.entrada_field.text
        sep = ' ' if actual and not actual.endswith('\n') else ''
        self.ids.entrada_field.text = (actual + sep + texto).strip()
        self.ids.lbl_estado_voz.text = f'✓ "{texto[:60]}..."' if len(texto) > 60 else f'✓ "{texto}"'
        self.ids.btn_mic.icon_color = (0.13, 0.40, 0.75, 1)
        self._escuchando = False

    def _voz_error(self, msg):
        self.ids.lbl_estado_voz.text = f'⚠ {msg}'
        self.ids.btn_mic.icon_color = (0.13, 0.40, 0.75, 1)
        self._escuchando = False

    def _mostrar(self, titulo, texto):
        dialog = MDDialog(
            title=titulo,
            text=texto,
            buttons=[MDFlatButton(text='OK', on_release=lambda x: dialog.dismiss())],
        )
        dialog.open()
