# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
from kivy.lang import Builder
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from utils.tarjetas_acuerdo import crear_tarjeta_acuerdo

Builder.load_string('''
<SeguimientoScreen>:
    MDBoxLayout:
        orientation: 'vertical'
        padding: '8dp'
        spacing: '6dp'

        MDLabel:
            text: "SEGUIMIENTO DE ACUERDOS"
            font_style: "H6"
            adaptive_height: True
            padding: [0, '4dp']

        MDScrollView:
            id: scroll_view
            MDBoxLayout:
                id: lista_acuerdos
                orientation: 'vertical'
                adaptive_height: True
                spacing: '6dp'
                padding: [0, '4dp']
''')


class SeguimientoScreen(MDScreen):
    _scroll_retry_events = None
    _load_event = None

    def on_pre_enter(self):
        self._load_event = Clock.schedule_once(lambda dt: self.cargar(), 0)

    def on_leave(self):
        # Ver nota completa en dashboard_screen.py.
        if self._load_event:
            self._load_event.cancel()
            self._load_event = None
        for ev in (self._scroll_retry_events or []):
            ev.cancel()
        self._scroll_retry_events = None

    def cargar(self):
        app = App.get_running_app()
        acuerdos = app.db.listar_todos_acuerdos()
        lista = self.ids.lista_acuerdos
        lista.clear_widgets()
        if not acuerdos:
            lista.add_widget(MDLabel(
                text='Sin acuerdos registrados.',
                halign='center',
                adaptive_height=True,
                padding=[0, dp(20)],
            ))
            self._forzar_scroll_arriba()
            return
        for ac in acuerdos:
            lista.add_widget(self._crear_card(ac))
        self._forzar_scroll_arriba()

    def _forzar_scroll_arriba(self):
        # Ver nota completa en dashboard_screen.py.
        sv = self.ids.scroll_view

        def _reset(dt=None):
            sv.scroll_y = 1
            sv.update_from_scroll()

        _reset()
        self._scroll_retry_events = [
            Clock.schedule_once(_reset, delay)
            for delay in (0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0)
        ]

    def _crear_card(self, ac):
        return crear_tarjeta_acuerdo(
            ac,
            on_toggle_estado=self._toggle_estado,
            on_ver_reunion=self._ver_reunion,
            mostrar_reunion=True,
        )

    def _toggle_estado(self, acuerdo_id, estaba_completado):
        app = App.get_running_app()
        nuevo_estado = 'pendiente' if estaba_completado else 'completado'
        app.db.marcar_estado_acuerdo(acuerdo_id, nuevo_estado)
        self.cargar()

    def _ver_reunion(self, reunion_id):
        app = App.get_running_app()
        app.reunion_activa_id = reunion_id
        app._PARENT_SCREEN['detalle_reunion'] = 'seguimiento'
        app.go_to('detalle_reunion')
