# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
from datetime import datetime
from kivy.lang import Builder
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.card import MDCard
from utils.widgets import CampoOrtografico
from utils.fechas import fecha_larga
from utils.voz import DictadoVoz
from utils.notas_acuerdos import separar as separar_notas_acuerdos, MARCADOR as MARCADOR_ACUERDOS

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
                icon: "eraser"
                on_press: root.borrar_seleccion()

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
        CampoOrtografico:
            id: entrada_field
            hint_text: "Escribe aquí con lápiz, teclado o voz..."
            mode: "rectangle"
            multiline: True
            size_hint_y: None
            height: '160dp'
            font_size: '15sp'
            padding: ['8dp', '8dp']

        # Responsable (opcional)
        MDTextField:
            id: responsable_field
            hint_text: "Responsable (opcional)"
            mode: "rectangle"
            font_size: '14sp'
            size_hint_y: None
            height: '48dp'

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

    def on_pre_enter(self):
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self._cargar(), 0)

    def _cargar(self):
        app = App.get_running_app()
        self._reunion_id = getattr(app, 'reunion_activa_id', None)
        self._acuerdos = []
        self.ids.lista_acuerdos.clear_widgets()
        self.ids.entrada_field.text = ''
        self.ids.responsable_field.text = ''
        self.ids.plazo_field.text = ''
        self.ids.lbl_estado_voz.text = ''

        if self._reunion_id:
            r = app.db.obtener_reunion(self._reunion_id)
            if r:
                self.ids.lbl_asunto_activo.text = r['asunto']
                self.ids.lbl_hora_activa.text = f"{fecha_larga(r['fecha'])}  {r['hora']}  —  {r['lugar'] or 'Sin lugar'}"
                # Cargar acuerdos previos desde notas si hay
                _, bloque = separar_notas_acuerdos(r.get('notas', ''))
                if bloque:
                    for linea in bloque.split('\n'):
                        linea = linea.strip()
                        if linea.startswith('•'):
                            self._acuerdos.append({'texto': linea[1:].strip(), 'plazo': ''})
                self._refrescar_lista()

    def enfocar_campo(self):
        self.ids.entrada_field.focus = True

    def borrar_seleccion(self):
        campo = self.ids.entrada_field
        if campo.selection_text:
            campo.delete_selection()

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
        responsable = self.ids.responsable_field.text.strip()
        plazo = self.ids.plazo_field.text.strip()
        ts = datetime.now().strftime('%H:%M')
        plazo_label = f' — plazo: {plazo}' if plazo else ''
        resp_label = f' — responsable: {responsable}' if responsable else ''
        acuerdo = f'[{ts}] {texto}{resp_label}{plazo_label}'
        self._acuerdos.append({'texto': acuerdo, 'plazo': plazo, 'responsable': responsable})
        self.ids.entrada_field.text = ''
        self.ids.responsable_field.text = ''
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
        n = self._guardar_acuerdos_en_bd()
        self._refrescar_lista()
        if n:
            self._mostrar('Guardado', f'{n} acuerdo(s) guardados en las notas de la reunión.')
        else:
            self._mostrar('Guardado', 'Los acuerdos ya estaban guardados en las notas de la reunión.')

    def _guardar_acuerdos_en_bd(self):
        """Vuelca self._acuerdos a la BD (notas + tabla acuerdos con plazo).
        Separado de guardar_en_notas() para poder llamarlo en silencio desde
        on_leave() -- antes los acuerdos capturados en vivo solo vivian en
        memoria hasta tocar "GUARDAR EN NOTAS" a mano, sin autoguardado ni
        aviso: una llamada entrante, el telefono trabandose, o tocar
        VOLVER/atras por error a media reunion perdia todo lo capturado sin
        ninguna advertencia.

        Devuelve cuantos acuerdos NUEVOS se anadieron al bloque de notas.

        El bloque de notas se reconstruye a partir de los bullets que YA
        estan en las notas mas los que falten de self._acuerdos -- no solo
        con self._acuerdos. Sin esto, como guardar vacia self._acuerdos,
        pulsar "GUARDAR EN NOTAS", agregar mas acuerdos y luego salir (o que
        entre una llamada -> on_leave) reescribia el bloque solo con los
        ultimos y borraba en silencio los guardados antes."""
        if not self._acuerdos or not self._reunion_id:
            return 0
        app = App.get_running_app()
        r = app.db.obtener_reunion(self._reunion_id)
        if not r:
            return 0
        notas_prev, bloque_prev = separar_notas_acuerdos(r.get('notas', ''))
        textos = [
            linea[1:].strip()
            for linea in bloque_prev.split('\n')
            if linea.strip().startswith('•')
        ]
        nuevos = 0
        for a in self._acuerdos:
            texto = a['texto'] if isinstance(a, dict) else a
            if texto in textos:
                continue
            textos.append(texto)
            nuevos += 1
            if isinstance(a, dict) and a.get('plazo'):
                app.db.guardar_acuerdo(self._reunion_id, a['texto'], a['plazo'], a.get('responsable', ''))
        bloque = f'\n\n{MARCADOR_ACUERDOS}\n' + '\n'.join(f'• {t}' for t in textos)
        nuevas_notas = (notas_prev + bloque).strip()
        app.db.actualizar_reunion(self._reunion_id, notas=nuevas_notas)
        # Repoblar desde el bloque ya escrito: la lista sigue mostrando todo
        # lo capturado (antes se vaciaba tras guardar) y un guardado
        # posterior no vuelve a insertar en la tabla `acuerdos` (plazo='').
        self._acuerdos = [{'texto': t, 'plazo': ''} for t in textos]
        return nuevos

    def on_leave(self):
        self._guardar_acuerdos_en_bd()

    # ── Voz ──────────────────────────────────────────────────────────
    # Antes esta pantalla reimplementaba el dictado desde cero (duplicando
    # utils/voz.py::DictadoVoz, que ya usan Nueva Reunión/Detalle/Perfil/
    # Login) y encima reasignaba entrada_field.text directo en vez de
    # insert_text() -- funciona hoy porque entrada_field no tiene
    # transformaciones propias, pero es el mismo tipo de atajo que costó
    # varias iteraciones arreglar en otros campos (ver CampoAcuerdosNumerados
    # en memoria del proyecto). Se unifica con la clase compartida.

    _dictado = None

    def toggle_voz(self):
        if self._dictado is None:
            self._dictado = DictadoVoz(
                campo=self.ids.entrada_field,
                boton_mic=self.ids.btn_mic,
                lbl_estado=self.ids.lbl_estado_voz,
                on_permiso_denegado=lambda msg: self._mostrar('Permiso requerido', msg),
            )
        self._dictado.toggle()

    def _mostrar(self, titulo, texto):
        dialog = MDDialog(
            title=titulo,
            text=texto,
            buttons=[MDFlatButton(text='OK', on_release=lambda x: dialog.dismiss())],
        )
        dialog.open()
