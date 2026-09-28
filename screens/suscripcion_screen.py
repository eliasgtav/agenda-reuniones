# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Pantalla de suscripción (paywall). Se muestra en vez del resto de la app
cuando utils.suscripcion.esta_activa() es False -- main.py se encarga de
forzarla y de ocultar la barra de navegación inferior mientras esté activa,
igual que ya hace con Login. No tiene botón para saltarla."""
from kivy.lang import Builder
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from utils.widgets import BotonPlano
from utils.dialogos import mostrar_info
from utils import suscripcion

Builder.load_string('''
<SuscripcionScreen>:
    MDScrollView:
        MDBoxLayout:
            orientation: 'vertical'
            padding: '24dp'
            spacing: '16dp'
            adaptive_height: True
            md_bg_color: app.theme_cls.bg_normal

            MDLabel:
                text: "Suscripción requerida"
                font_style: "H5"
                halign: "center"
                adaptive_height: True

            MDLabel:
                text: "Prueba gratis de 15 días, luego continúa con el plan que prefieras."
                font_style: "Body1"
                halign: "center"
                adaptive_height: True
                theme_text_color: "Secondary"

            MDLabel:
                id: lbl_aviso_offline
                text: ""
                font_style: "Caption"
                halign: "center"
                adaptive_height: True
                theme_text_color: "Custom"
                text_color: 0.80, 0.15, 0.15, 1

            MDCard:
                orientation: 'vertical'
                padding: '16dp'
                spacing: '8dp'
                size_hint_y: None
                adaptive_height: True
                radius: [12]
                line_color: 0.85, 0.85, 0.85, 1
                line_width: 1
                md_bg_color: 1, 1, 1, 1

                MDLabel:
                    text: "Plan Mensual"
                    font_style: "Subtitle1"
                    bold: True
                    adaptive_height: True

                MDLabel:
                    id: lbl_precio_mensual
                    text: "Consultando precio..."
                    font_style: "Body2"
                    adaptive_height: True
                    theme_text_color: "Secondary"

                BotonPlano:
                    text: "SUSCRIBIRME (MENSUAL)"
                    size_hint_x: None
                    width: dp(240)
                    pos_hint: {"center_x": .5}
                    _radius: dp(14)
                    md_bg_color: 0.13, 0.40, 0.75, 1
                    on_release: root.suscribirse('mensual')

            MDCard:
                orientation: 'vertical'
                padding: '16dp'
                spacing: '8dp'
                size_hint_y: None
                adaptive_height: True
                radius: [12]
                line_color: 0.85, 0.85, 0.85, 1
                line_width: 1
                md_bg_color: 1, 1, 1, 1

                MDLabel:
                    text: "Plan Anual"
                    font_style: "Subtitle1"
                    bold: True
                    adaptive_height: True

                MDLabel:
                    id: lbl_precio_anual
                    text: "Consultando precio..."
                    font_style: "Body2"
                    adaptive_height: True
                    theme_text_color: "Secondary"

                BotonPlano:
                    text: "SUSCRIBIRME (ANUAL)"
                    size_hint_x: None
                    width: dp(240)
                    pos_hint: {"center_x": .5}
                    _radius: dp(14)
                    md_bg_color: 0.13, 0.40, 0.75, 1
                    on_release: root.suscribirse('anual')

            MDLabel:
                text: "© Elías Gaytan Alvino"
                font_style: "Caption"
                halign: "center"
                adaptive_height: True
                theme_text_color: "Hint"
''')


class SuscripcionScreen(MDScreen):

    def on_pre_enter(self):
        Clock.schedule_once(lambda dt: self._refrescar(), 0)

    def _refrescar(self):
        if suscripcion.en_gracia_offline():
            self.ids.lbl_aviso_offline.text = (
                'No se pudo confirmar tu suscripción por falta de conexión. '
                'Conéctate a internet para seguir usando la app.'
            )
        else:
            self.ids.lbl_aviso_offline.text = ''
        suscripcion.consultar_precios(self._pintar_precios)

    def _pintar_precios(self, precios):
        def _pintar(dt):
            self.ids.lbl_precio_mensual.text = precios.get('mensual', 'Ver precio en Google Play')
            self.ids.lbl_precio_anual.text = precios.get('anual', 'Ver precio en Google Play')
        Clock.schedule_once(_pintar, 0)

    def suscribirse(self, plan):
        def _resultado(ok, mensaje):
            if not ok:
                Clock.schedule_once(lambda dt: mostrar_info('Suscripción', mensaje), 0)
        suscripcion.comprar(plan, on_resultado=_resultado)
