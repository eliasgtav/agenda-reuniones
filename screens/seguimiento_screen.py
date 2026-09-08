# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
from kivy.lang import Builder
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from utils.tarjetas_acuerdo import crear_tarjeta_acuerdo
from utils.mixins_pantalla import ScrollArribaMixin, PaginacionMixin

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
            on_scroll_y: root._on_scroll_y(self.scroll_y)
            MDBoxLayout:
                id: lista_acuerdos
                orientation: 'vertical'
                adaptive_height: True
                spacing: '6dp'
                padding: [0, '4dp']
''')


class SeguimientoScreen(ScrollArribaMixin, PaginacionMixin, MDScreen):
    _load_event = None

    def on_pre_enter(self):
        self._load_event = Clock.schedule_once(lambda dt: self.cargar(), 0)

    def on_leave(self):
        if self._load_event:
            self._load_event.cancel()
            self._load_event = None
        self._cancelar_scroll_retries()

    def cargar(self):
        # Primera pagina aqui, el resto via cargar_mas() (heredado de
        # PaginacionMixin) al llegar cerca del final del scroll -- ver
        # benchmark en scripts/benchmark_carga.py.
        lista = self.ids.lista_acuerdos
        lista.clear_widgets()
        items = self._cargar_pagina(reset=True)
        if not items:
            lista.add_widget(MDLabel(
                text='Sin acuerdos registrados.',
                halign='center',
                adaptive_height=True,
                padding=[0, dp(20)],
            ))
        self._forzar_scroll_arriba()

    def _fetch_pagina(self, limit, offset):
        app = App.get_running_app()
        return app.db.listar_todos_acuerdos(limit=limit, offset=offset)

    def _agregar_item(self, ac):
        self.ids.lista_acuerdos.add_widget(self._crear_card(ac))

    def _crear_card(self, ac):
        # holder se llena justo despues de construir la tarjeta (antes de que
        # el usuario pueda tocar el checkbox), asi _toggle_estado puede
        # reemplazar solo esta tarjeta sin reconstruir la lista entera.
        holder = {}

        def _toggle(acuerdo_id, estaba_completado):
            self._toggle_estado(acuerdo_id, estaba_completado, holder.get('card'), ac)

        card = crear_tarjeta_acuerdo(
            ac,
            on_toggle_estado=_toggle,
            on_ver_reunion=self._ver_reunion,
            mostrar_reunion=True,
        )
        holder['card'] = card
        return card

    def _toggle_estado(self, acuerdo_id, estaba_completado, card, ac):
        nuevo_estado = 'pendiente' if estaba_completado else 'completado'
        App.get_running_app().db.marcar_estado_acuerdo(acuerdo_id, nuevo_estado)
        # Reemplazar SOLO esta tarjeta. self.cargar() reconstruia la lista
        # completa y volvia a la primera pagina + scroll arriba -- en la
        # pantalla cuya accion central es justamente marcar acuerdos, cada
        # tic tiraba al usuario al principio y colapsaba lo ya paginado.
        lista = self.ids.lista_acuerdos
        if card is None or card not in lista.children:
            self.cargar()
            return
        idx = lista.children.index(card)
        ac_actualizado = dict(ac)
        ac_actualizado['estado'] = nuevo_estado
        lista.remove_widget(card)
        lista.add_widget(self._crear_card(ac_actualizado), index=idx)

    def _ver_reunion(self, reunion_id):
        app = App.get_running_app()
        app.reunion_activa_id = reunion_id
        app._PARENT_SCREEN['detalle_reunion'] = 'seguimiento'
        app.go_to('detalle_reunion')
