# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
import os
import shutil
import threading
from datetime import datetime
from kivy.lang import Builder
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.pickers import MDDatePicker, MDTimePicker

Builder.load_string('''
<DetalleReunionScreen>:
    MDScrollView:
        MDBoxLayout:
            orientation: 'vertical'
            padding: '12dp'
            spacing: '10dp'
            adaptive_height: True

            MDCard:
                id: header_card
                orientation: 'vertical'
                padding: '12dp'
                size_hint_y: None
                height: '110dp'
                radius: [10]

                MDLabel:
                    id: lbl_asunto
                    text: ""
                    font_style: "H6"
                    adaptive_height: True

                MDLabel:
                    id: lbl_info
                    text: ""
                    font_style: "Caption"
                    adaptive_height: True

                MDLabel:
                    id: lbl_estado
                    text: ""
                    font_style: "Subtitle2"
                    adaptive_height: True

            MDBoxLayout:
                adaptive_height: True
                spacing: '6dp'

                MDRaisedButton:
                    text: "REALIZADA"
                    md_bg_color: 0.13, 0.55, 0.13, 1
                    on_release: root.cambiar_estado('realizada')
                    size_hint_x: .25

                MDRaisedButton:
                    text: "CANCELADA"
                    md_bg_color: 0.80, 0.13, 0.13, 1
                    on_release: root.cambiar_estado('cancelada')
                    size_hint_x: .25

                MDRaisedButton:
                    text: "NO ASISTÍ"
                    md_bg_color: 0.90, 0.40, 0.13, 1
                    on_release: root.cambiar_estado('no_asistida')
                    size_hint_x: .25

                MDRaisedButton:
                    id: btn_en_reunion
                    text: "EN REUNIÓN"
                    md_bg_color: 0.5, 0.5, 0.5, 1
                    disabled: True
                    on_release: root.abrir_en_reunion()
                    size_hint_x: .25

            MDLabel:
                text: "Participantes"
                font_style: "Subtitle1"
                adaptive_height: True

            MDBoxLayout:
                id: participantes_list
                orientation: 'vertical'
                adaptive_height: True
                spacing: '4dp'

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDTextField:
                    id: nuevo_participante
                    hint_text: "Agregar participante"
                    mode: "rectangle"
                    size_hint_x: .8

                MDIconButton:
                    icon: "account-plus"
                    on_release: root.agregar_participante()

            # ── Área de Trabajo ──────────────────────────────────────
            MDCard:
                orientation: 'vertical'
                padding: '12dp'
                spacing: '8dp'
                adaptive_height: True
                radius: [10]
                md_bg_color: 0.13, 0.40, 0.75, 0.07

                MDBoxLayout:
                    adaptive_height: True
                    spacing: '6dp'

                    MDLabel:
                        text: "DESARROLLO DE LA REUNIÓN"
                        font_style: "Subtitle1"
                        adaptive_height: True

                    MDIconButton:
                        icon: "pencil"
                        size_hint_x: None
                        width: '36dp'
                        on_release: root.enfocar_trabajo()

                    MDIconButton:
                        id: btn_mic
                        icon: "microphone"
                        size_hint_x: None
                        width: '36dp'
                        theme_icon_color: "Custom"
                        icon_color: 0.13, 0.40, 0.75, 1
                        on_release: root.toggle_voz()

                    MDIconButton:
                        icon: "delete-sweep"
                        size_hint_x: None
                        width: '36dp'
                        theme_icon_color: "Custom"
                        icon_color: 0.80, 0.13, 0.13, 1
                        on_release: root.limpiar_trabajo()

                MDTextField:
                    id: trabajo_field
                    hint_text: "Redacta aquí con lápiz, teclado o voz..."
                    mode: "rectangle"
                    multiline: True
                    size_hint_y: None
                    height: '280dp'
                    font_size: '15sp'

                MDLabel:
                    id: lbl_voz_estado
                    text: ""
                    font_style: "Caption"
                    halign: "center"
                    adaptive_height: True
                    theme_text_color: "Custom"
                    text_color: 0.13, 0.55, 0.13, 1

                MDRaisedButton:
                    text: "GUARDAR EN NOTAS"
                    pos_hint: {"center_x": .5}
                    md_bg_color: 0.13, 0.40, 0.75, 1
                    on_release: root.guardar_trabajo_en_notas()

            # ── Notas ────────────────────────────────────────────────
            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDLabel:
                    text: "OBJETIVOS DE LA REUNIÓN"
                    font_style: "Subtitle1"
                    adaptive_height: True

                MDIconButton:
                    icon: "pencil"
                    size_hint_x: None
                    width: '36dp'
                    on_release: root.enfocar_notas()

            MDTextField:
                id: notas_field
                hint_text: "Escribe las notas con lápiz o teclado..."
                mode: "rectangle"
                multiline: True
                size_hint_y: None
                height: '220dp'
                font_size: '15sp'

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDLabel:
                    text: "CIERRE Y ACUERDOS DE LA REUNIÓN"
                    font_style: "Subtitle1"
                    adaptive_height: True

                MDIconButton:
                    icon: "pencil"
                    size_hint_x: None
                    width: '36dp'
                    on_release: root.enfocar_conclusion()

            MDTextField:
                id: conclusion_field
                hint_text: "Escribe la conclusión con lápiz o teclado..."
                mode: "rectangle"
                multiline: True
                size_hint_y: None
                height: '220dp'
                font_size: '15sp'

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDLabel:
                    text: "Acuerdos con plazo de cumplimiento"
                    font_style: "Subtitle2"
                    adaptive_height: True
                    theme_text_color: "Custom"
                    text_color: 0.13, 0.40, 0.75, 1

                MDIconButton:
                    icon: "bell-plus"
                    theme_icon_color: "Custom"
                    icon_color: 0.13, 0.40, 0.75, 1
                    size_hint_x: None
                    width: '40dp'
                    on_release: root.agregar_acuerdo_plazo()

            MDBoxLayout:
                id: acuerdos_plazo_list
                orientation: 'vertical'
                adaptive_height: True
                spacing: '4dp'

            MDLabel:
                text: "Archivos adjuntos"
                font_style: "Subtitle1"
                adaptive_height: True

            MDBoxLayout:
                id: archivos_list
                orientation: 'vertical'
                adaptive_height: True
                spacing: '4dp'

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDRaisedButton:
                    id: btn_grabar
                    text: "GRABAR REUNIÓN"
                    md_bg_color: 0.13, 0.40, 0.75, 1
                    on_release: root.toggle_grabacion()

                MDRaisedButton:
                    text: "ADJUNTAR ARCHIVO"
                    md_bg_color: 0.40, 0.23, 0.72, 1
                    on_release: root.adjuntar_archivo()

            MDBoxLayout:
                adaptive_height: True
                spacing: '8dp'

                MDRaisedButton:
                    text: "GUARDAR CAMBIOS"
                    md_bg_color: 0.13, 0.40, 0.75, 1
                    on_release: root.guardar_cambios()

                MDRaisedButton:
                    text: "TERMINAR REUNIÓN"
                    md_bg_color: 0.13, 0.55, 0.13, 1
                    on_release: root.terminar_reunion()

                MDFlatButton:
                    text: "VOLVER"
                    on_release: app.go_back()

            MDCard:
                orientation: 'vertical'
                padding: '12dp'
                spacing: '10dp'
                adaptive_height: True
                radius: [10]
                md_bg_color: 0.40, 0.23, 0.72, 0.08

                MDLabel:
                    text: "Reprogramar reunión"
                    font_style: "Subtitle1"
                    adaptive_height: True
                    halign: "center"

                MDBoxLayout:
                    adaptive_height: True
                    spacing: '8dp'

                    MDRaisedButton:
                        id: btn_nueva_fecha
                        text: "Seleccionar fecha"
                        on_release: root.abrir_fecha_reprog()
                        md_bg_color: 0.40, 0.23, 0.72, 1

                    MDRaisedButton:
                        id: btn_nueva_hora
                        text: "Seleccionar hora"
                        on_release: root.abrir_hora_reprog()
                        md_bg_color: 0.40, 0.23, 0.72, 1

                MDRaisedButton:
                    text: "CONFIRMAR REPROGRAMACIÓN"
                    on_release: root.reprogramar()
                    md_bg_color: 0.13, 0.55, 0.13, 1
                    pos_hint: {"center_x": .5}
''')

COLORES_ESTADO = {
    'pendiente':   (1.00, 0.98, 0.77, 1),
    'realizada':   (0.78, 0.90, 0.79, 1),
    'cancelada':   (1.00, 0.80, 0.82, 1),
    'no_asistida': (1.00, 0.88, 0.70, 1),
}

_grabando = False
_grabacion_path = None


class DetalleReunionScreen(MDScreen):
    _reunion_id = None
    _nueva_fecha = None
    _nueva_hora = None
    _check_hora_event = None

    def on_pre_enter(self):
        from kivy.clock import Clock
        def _load(dt):
            app = App.get_running_app()
            self._reunion_id = getattr(app, 'reunion_activa_id', None)
            if self._reunion_id:
                self.cargar()
                self._verificar_hora_reunion()
                if self._check_hora_event:
                    self._check_hora_event.cancel()
                self._check_hora_event = Clock.schedule_interval(
                    lambda dt: self._verificar_hora_reunion(), 10
                )
        Clock.schedule_once(_load, 0)

    def on_leave(self):
        if self._check_hora_event:
            self._check_hora_event.cancel()
            self._check_hora_event = None

    def _verificar_hora_reunion(self):
        if not self._reunion_id:
            return
        r = App.get_running_app().db.obtener_reunion(self._reunion_id)
        if not r:
            return
        try:
            from datetime import datetime
            dt_reunion = datetime.strptime(f"{r['fecha']} {r['hora']}", '%Y-%m-%d %H:%M')
            ahora = datetime.now()
            activa = ahora >= dt_reunion and r['estado'] == 'pendiente'
            self.ids.btn_en_reunion.disabled = not activa
            self.ids.btn_en_reunion.md_bg_color = (
                (0.8, 0.1, 0.1, 1) if activa else (0.5, 0.5, 0.5, 1)
            )
            if activa:
                self.ids.lbl_estado.text = 'Estado: EN REUNIÓN — ¡Es hora!'
            else:
                segs = (dt_reunion - ahora).total_seconds()
                mins = int(segs / 60) + (1 if segs % 60 > 0 else 0)
                if mins < 60:
                    self.ids.lbl_estado.text = f'Estado: {r["estado"].upper()} — EN REUNIÓN se activa en {mins} min'
                else:
                    horas = mins // 60
                    self.ids.lbl_estado.text = f'Estado: {r["estado"].upper()} — EN REUNIÓN en {horas}h {mins % 60}min'
        except Exception:
            pass

    def abrir_en_reunion(self):
        App.get_running_app().go_to('en_reunion')

    def cargar(self):
        app = App.get_running_app()
        db = app.db
        r = db.obtener_reunion(self._reunion_id)
        if not r:
            return

        color = COLORES_ESTADO.get(r['estado'], (0.95, 0.95, 0.95, 1))
        self.ids.header_card.md_bg_color = color
        self.ids.lbl_asunto.text = r['asunto']
        self.ids.lbl_info.text = f"{r['fecha']}  {r['hora']}  —  {r['lugar'] or 'Sin lugar'}"
        self.ids.lbl_estado.text = f"Estado: {r['estado'].upper()}"
        self.ids.notas_field.text = r['notas'] or ''
        self.ids.conclusion_field.text = r['conclusion'] or ''

        self._cargar_participantes(db)
        self._cargar_archivos(db)
        self._cargar_acuerdos_plazo()

    def _cargar_participantes(self, db):
        lista = self.ids.participantes_list
        lista.clear_widgets()
        for p in db.listar_participantes(self._reunion_id):
            fila = MDBoxLayout(adaptive_height=True, spacing=dp(8))
            fila.add_widget(MDLabel(
                text=p['nombre'],
                adaptive_height=True,
                font_style='Body2',
            ))

            cb = MDCheckbox(active=bool(p['asistio']), size_hint_x=None, width=dp(40))
            pid = p['id']
            cb.bind(active=lambda inst, val, i=pid: db.actualizar_asistencia(i, int(val)))
            fila.add_widget(cb)
            fila.add_widget(MDLabel(text='Asistió', adaptive_height=True, font_style='Caption'))

            btn_del = MDIconButton(icon='delete', size_hint_x=None, width=dp(40))
            btn_del.bind(on_release=lambda _, i=pid: self._borrar_participante(i))
            fila.add_widget(btn_del)
            lista.add_widget(fila)

    def _borrar_participante(self, pid):
        App.get_running_app().db.eliminar_participante(pid)
        self.cargar()

    def agregar_participante(self):
        nombre = self.ids.nuevo_participante.text.strip()
        if not nombre:
            return
        db = App.get_running_app().db
        db.agregar_participante(self._reunion_id, nombre)
        self.ids.nuevo_participante.text = ''
        self._cargar_participantes(db)

    def _cargar_archivos(self, db):
        lista = self.ids.archivos_list
        lista.clear_widgets()
        for a in db.listar_archivos(self._reunion_id):
            fila = MDBoxLayout(adaptive_height=True, spacing=dp(6))
            fila.add_widget(MDLabel(
                text=a['nombre'],
                adaptive_height=True,
                font_style='Body2',
                shorten=True,
                shorten_from='right',
            ))
            aid = a['id']
            btn_del = MDIconButton(icon='delete', size_hint_x=None, width=dp(40))
            btn_del.bind(on_release=lambda _, i=aid: self._borrar_archivo(i))
            fila.add_widget(btn_del)
            lista.add_widget(fila)

    def _borrar_archivo(self, aid):
        def _confirmar(_):
            dialog.dismiss()
            App.get_running_app().db.eliminar_archivo(aid)
            self.cargar()

        dialog = MDDialog(
            title='Eliminar archivo',
            text='¿Estás seguro de que deseas eliminar este archivo adjunto? Esta acción no se puede deshacer.',
            buttons=[
                MDFlatButton(text='CANCELAR', on_release=lambda x: dialog.dismiss()),
                MDRaisedButton(
                    text='ELIMINAR',
                    md_bg_color=(0.8, 0.1, 0.1, 1),
                    on_release=_confirmar,
                ),
            ],
        )
        dialog.open()

    def adjuntar_archivo(self):
        try:
            from plyer import filechooser

            def _on_seleccion(seleccion):
                if not seleccion:
                    return
                ruta_orig = seleccion[0]
                nombre = os.path.basename(ruta_orig)
                if platform == 'android':
                    from android.storage import app_storage_path
                    dest_dir = os.path.join(app_storage_path(), 'adjuntos')
                else:
                    dest_dir = os.path.join(os.path.expanduser('~'), 'agenda_adjuntos')
                os.makedirs(dest_dir, exist_ok=True)
                dest = os.path.join(dest_dir, nombre)
                shutil.copy2(ruta_orig, dest)
                db = App.get_running_app().db
                db.agregar_archivo(self._reunion_id, nombre, dest)
                self._cargar_archivos(db)

            filechooser.open_file(on_selection=_on_seleccion)
        except Exception as e:
            self._mostrar_info('Error', str(e))

    def cambiar_estado(self, nuevo_estado):
        db = App.get_running_app().db
        db.actualizar_reunion(self._reunion_id, estado=nuevo_estado)
        self.cargar()

    def guardar_cambios(self):
        db = App.get_running_app().db
        db.actualizar_reunion(
            self._reunion_id,
            notas=self.ids.notas_field.text,
            conclusion=self.ids.conclusion_field.text,
        )
        self._mostrar_info('Guardado', 'Cambios guardados correctamente.')

    def terminar_reunion(self):
        app = App.get_running_app()
        db = app.db
        db.actualizar_reunion(
            self._reunion_id,
            estado='realizada',
            conclusion=self.ids.conclusion_field.text,
            notas=self.ids.notas_field.text,
        )
        from utils.config import cargar as cargar_config
        config = cargar_config()
        tiene_correo = bool(config.get('correo_origen') and config.get('correo_password') and config.get('correo_destino'))
        msg_extra = '\nEnviando acta por correo...' if tiene_correo else ''
        self._mostrar_info('Reunión terminada', f'La reunión fue marcada como realizada.{msg_extra}')
        self._enviar_acta_correo(db)

    def _enviar_acta_correo(self, db):
        from utils.email_sender import enviar_acta
        from utils.config import cargar as cargar_config
        from kivy.clock import Clock
        config = cargar_config()

        # Si no hay correo configurado, omitir silenciosamente
        if not config.get('correo_origen') or not config.get('correo_password') or not config.get('correo_destino'):
            return

        reunion = db.obtener_reunion(self._reunion_id)
        participantes = db.listar_participantes(self._reunion_id)

        def _resultado(ok, msg):
            Clock.schedule_once(lambda dt: self._mostrar_info(
                '✓ Acta enviada' if ok else '⚠ Correo no enviado', msg
            ), 0)

        enviar_acta(reunion, participantes, config, callback=_resultado)

    # ── Área de Trabajo ──────────────────────────────────────────────

    def enfocar_trabajo(self):
        self.ids.trabajo_field.focus = True

    def limpiar_trabajo(self):
        self.ids.trabajo_field.text = ''
        self.ids.lbl_voz_estado.text = ''

    def guardar_trabajo_en_notas(self):
        contenido = self.ids.trabajo_field.text.strip()
        if not contenido:
            self._mostrar_info('Aviso', 'El área de trabajo está vacía.')
            return
        actual = self.ids.notas_field.text
        separador = '\n\n--- ' + datetime.now().strftime('%H:%M') + ' ---\n'
        self.ids.notas_field.text = (actual + separador + contenido).strip()
        self.ids.trabajo_field.text = ''
        self.ids.lbl_voz_estado.text = '✓ Contenido guardado en Notas'

    _escuchando = False

    def toggle_voz(self):
        if self._escuchando:
            return
        self._escuchando = True
        self.ids.btn_mic.icon_color = (0.8, 0.1, 0.1, 1)
        self.ids.lbl_voz_estado.text = '🎤 Escuchando... habla ahora'
        import threading
        threading.Thread(target=self._escuchar_voz, daemon=True).start()

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
            Clock.schedule_once(lambda dt: self._insertar_texto_voz(texto), 0)
        except sr.WaitTimeoutError:
            Clock.schedule_once(lambda dt: self._voz_error('Tiempo agotado. No se detectó voz.'), 0)
        except sr.UnknownValueError:
            Clock.schedule_once(lambda dt: self._voz_error('No se entendió lo que dijiste. Intenta de nuevo.'), 0)
        except sr.RequestError:
            Clock.schedule_once(lambda dt: self._voz_error('Sin conexión a internet para reconocimiento de voz.'), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._voz_error(f'Error: {e}'), 0)

    def _insertar_texto_voz(self, texto):
        campo = self.ids.trabajo_field
        actual = campo.text
        campo.text = (actual + (' ' if actual and not actual.endswith('\n') else '') + texto).strip()
        self.ids.lbl_voz_estado.text = f'✓ Voz reconocida: "{texto[:50]}..."' if len(texto) > 50 else f'✓ Voz: "{texto}"'
        self.ids.btn_mic.icon_color = (0.13, 0.40, 0.75, 1)
        self._escuchando = False

    def _voz_error(self, msg):
        self.ids.lbl_voz_estado.text = f'⚠ {msg}'
        self.ids.btn_mic.icon_color = (0.13, 0.40, 0.75, 1)
        self._escuchando = False

    # ── Notas ─────────────────────────────────────────────────────────

    def enfocar_notas(self):
        self.ids.notas_field.focus = True

    def enfocar_conclusion(self):
        self.ids.conclusion_field.focus = True

    # ── Acuerdos con plazo ────────────────────────────────────────────

    def _cargar_acuerdos_plazo(self):
        app = App.get_running_app()
        acuerdos = app.db.listar_acuerdos(self._reunion_id)
        lista = self.ids.acuerdos_plazo_list
        lista.clear_widgets()
        if not acuerdos:
            lista.add_widget(MDLabel(
                text='Sin acuerdos con plazo registrados.',
                font_style='Caption',
                adaptive_height=True,
                theme_text_color='Secondary',
            ))
            return
        for ac in acuerdos:
            self._agregar_card_acuerdo(lista, ac)

    def _agregar_card_acuerdo(self, lista, ac):
        from datetime import datetime
        hoy = datetime.now().strftime('%Y-%m-%d')
        plazo = ac.get('plazo', '')
        if plazo < hoy:
            color = (0.8, 0.1, 0.1, 0.12)
            icono = 'alert-circle'
        elif plazo == hoy:
            color = (0.9, 0.5, 0.0, 0.12)
            icono = 'bell-ring'
        else:
            color = (0.13, 0.55, 0.13, 0.10)
            icono = 'bell-check'

        card = MDCard(
            orientation='horizontal',
            padding=dp(8),
            size_hint_y=None,
            height=dp(56),
            radius=[8],
            md_bg_color=color,
        )
        lbl = MDLabel(
            text=f'• {ac["texto"]}\n  Plazo: {plazo}',
            font_style='Caption',
            adaptive_height=True,
        )
        btn_del = MDIconButton(
            icon='close',
            size_hint_x=None,
            width=dp(36),
        )
        ac_id = ac['id']
        btn_del.bind(on_release=lambda _, i=ac_id: self._eliminar_acuerdo_plazo(i))
        card.add_widget(MDIconButton(icon=icono, size_hint_x=None, width=dp(36), disabled=True))
        card.add_widget(lbl)
        card.add_widget(btn_del)
        lista.add_widget(card)

    def _eliminar_acuerdo_plazo(self, acuerdo_id):
        App.get_running_app().db.eliminar_acuerdo(acuerdo_id)
        self._cargar_acuerdos_plazo()

    def agregar_acuerdo_plazo(self):
        self._texto_nuevo_acuerdo = ''
        self._plazo_nuevo_acuerdo = ''

        from kivymd.uix.textfield import MDTextField as TF
        from kivymd.uix.button import MDRaisedButton as MRB

        campo_texto = TF(hint_text='Descripción del acuerdo', mode='rectangle')
        campo_plazo = TF(hint_text='Plazo (YYYY-MM-DD)', mode='rectangle')
        campo_plazo.bind(on_focus=lambda inst, val: self._abrir_cal_acuerdo(inst, campo_plazo) if val else None)

        contenido = MDBoxLayout(orientation='vertical', adaptive_height=True, spacing=dp(8), padding=[0, dp(8)])
        contenido.add_widget(campo_texto)
        contenido.add_widget(campo_plazo)

        self._dlg_acuerdo = MDDialog(
            title='Nuevo acuerdo con plazo',
            type='custom',
            content_cls=contenido,
            buttons=[
                MDFlatButton(text='CANCELAR', on_release=lambda x: self._dlg_acuerdo.dismiss()),
                MDRaisedButton(
                    text='GUARDAR',
                    on_release=lambda x: self._guardar_nuevo_acuerdo(campo_texto.text, campo_plazo.text),
                ),
            ],
        )
        self._dlg_acuerdo.open()

    def _abrir_cal_acuerdo(self, instance, campo):
        picker = MDDatePicker()
        picker.bind(on_save=lambda inst, val, *a: setattr(campo, 'text', val.strftime('%Y-%m-%d')))
        picker.open()

    def _guardar_nuevo_acuerdo(self, texto, plazo):
        texto = texto.strip()
        plazo = plazo.strip()
        if not texto or not plazo:
            self._mostrar_info('Aviso', 'Escribe el acuerdo y selecciona un plazo.')
            return
        self._dlg_acuerdo.dismiss()
        App.get_running_app().db.guardar_acuerdo(self._reunion_id, texto, plazo)
        self._cargar_acuerdos_plazo()

    def abrir_fecha_reprog(self):
        picker = MDDatePicker()
        picker.bind(on_save=self._on_fecha_reprog)
        picker.open()

    def _on_fecha_reprog(self, instance, value, *args):
        self._nueva_fecha = value.strftime('%Y-%m-%d')
        self.ids.btn_nueva_fecha.text = self._nueva_fecha

    def abrir_hora_reprog(self):
        picker = MDTimePicker()
        picker.bind(on_save=self._on_hora_reprog)
        picker.open()
        Clock.schedule_once(lambda dt: picker._switch_input(), 0.3)

    def _on_hora_reprog(self, instance, value):
        self._nueva_hora = value.strftime('%H:%M')
        self.ids.btn_nueva_hora.text = self._nueva_hora

    def reprogramar(self):
        if not self._reunion_id:
            self._mostrar_info('Error', 'No hay reunión seleccionada.')
            return
        if not self._nueva_fecha and not self._nueva_hora:
            self._mostrar_info('Atención', 'Selecciona al menos una nueva fecha o una nueva hora.')
            return
        db = App.get_running_app().db
        kwargs = {}
        if self._nueva_fecha:
            kwargs['fecha'] = self._nueva_fecha
        if self._nueva_hora:
            kwargs['hora'] = self._nueva_hora
        db.actualizar_reunion(self._reunion_id, **kwargs)
        partes = []
        if self._nueva_fecha:
            partes.append(f'fecha: {self._nueva_fecha}')
        if self._nueva_hora:
            partes.append(f'hora: {self._nueva_hora}')
        self._mostrar_info('Reprogramada', f'Reunión actualizada — {", ".join(partes)}.')
        self._nueva_fecha = None
        self._nueva_hora = None
        self.ids.btn_nueva_fecha.text = 'Seleccionar fecha'
        self.ids.btn_nueva_hora.text = 'Seleccionar hora'
        self.cargar()

    def toggle_grabacion(self):
        global _grabando, _grabacion_path
        if not _grabando:
            self._iniciar_grabacion()
        else:
            self._detener_grabacion()

    def _iniciar_grabacion(self):
        global _grabando, _grabacion_path
        try:
            from plyer import audio
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            if platform == 'android':
                from android.storage import app_storage_path
                dest_dir = app_storage_path()
            else:
                dest_dir = os.path.expanduser('~')
            _grabacion_path = os.path.join(dest_dir, f'reunion_{ts}.wav')
            audio.start()
            _grabando = True
            self.ids.btn_grabar.text = 'DETENER GRABACIÓN'
            self.ids.btn_grabar.md_bg_color = (0.8, 0.1, 0.1, 1)
        except Exception as e:
            self._mostrar_info('Grabación', f'No disponible: {e}')

    def _detener_grabacion(self):
        global _grabando, _grabacion_path
        try:
            from plyer import audio
            audio.stop()
        except Exception:
            pass
        _grabando = False
        self.ids.btn_grabar.text = 'GRABAR REUNIÓN'
        self.ids.btn_grabar.md_bg_color = (0.13, 0.40, 0.75, 1)
        if _grabacion_path:
            App.get_running_app().db.actualizar_reunion(
                self._reunion_id, grabacion_path=_grabacion_path
            )
            nombre = os.path.basename(_grabacion_path)
            App.get_running_app().db.agregar_archivo(
                self._reunion_id, nombre, _grabacion_path, 'audio'
            )
            self._cargar_archivos(App.get_running_app().db)

    def _mostrar_info(self, titulo, texto):
        dialog = MDDialog(
            title=titulo,
            text=texto,
            buttons=[MDFlatButton(text='OK', on_release=lambda x: dialog.dismiss())],
        )
        dialog.open()
