# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
from kivy.lang import Builder
from kivy.app import App
from kivy.metrics import dp
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from utils.config import cargar as cargar_config

Builder.load_string('''
<DashboardScreen>:
    MDScrollView:
        MDBoxLayout:
            orientation: 'vertical'
            padding: '16dp'
            spacing: '12dp'
            adaptive_height: True

            # Encabezado de perfil
            MDCard:
                orientation: 'horizontal'
                padding: '12dp'
                spacing: '12dp'
                size_hint_y: None
                height: '90dp'
                radius: [12]
                md_bg_color: 0.13, 0.40, 0.75, 0.15
                on_release: app.go_to('perfil')
                ripple_behavior: True

                MDCard:
                    id: avatar_card
                    size_hint: None, None
                    size: '64dp', '64dp'
                    radius: [32]
                    md_bg_color: .75, .75, .75, 1

                    Image:
                        id: avatar_img
                        source: ""
                        allow_stretch: True
                        keep_ratio: False

                MDBoxLayout:
                    orientation: 'vertical'

                    MDLabel:
                        id: lbl_nombre
                        text: "Usuario"
                        font_style: "Subtitle1"
                        adaptive_height: True

                    MDLabel:
                        text: "Toca para editar perfil"
                        font_style: "Caption"
                        adaptive_height: True
                        theme_text_color: "Secondary"

            MDLabel:
                text: "Resumen General"
                font_style: "H6"
                adaptive_height: True
                padding: [0, '8dp']

            MDGridLayout:
                id: stats_grid
                cols: 2
                adaptive_height: True
                spacing: '8dp'

            MDLabel:
                text: "Reuniones de Hoy"
                font_style: "H6"
                adaptive_height: True
                padding: [0, '8dp']

            MDBoxLayout:
                id: lista_hoy
                orientation: 'vertical'
                adaptive_height: True
                spacing: '6dp'


            MDRaisedButton:
                text: "VER TODAS LAS REUNIONES"
                pos_hint: {'center_x': .5}
                on_release: app.go_to('lista_reuniones')

            MDLabel:
                text: "© Elías Gaytan Alvino"
                font_style: "Caption"
                halign: "center"
                adaptive_height: True
                padding: [0, '16dp']
''')

COLORES_ESTADO = {
    'pendiente':   (1.0, 0.98, 0.77, 1),
    'realizada':   (0.78, 0.90, 0.79, 1),
    'cancelada':   (1.0, 0.80, 0.82, 1),
    'no_asistida': (1.0, 0.88, 0.70, 1),
}

STAT_CONFIG = [
    ('hoy',         'Hoy',          (0.13, 0.40, 0.75, 1)),
    ('pendientes',  'Pendientes',   (1.0, 0.75, 0.0, 1)),
    ('realizadas',  'Realizadas',   (0.18, 0.65, 0.28, 1)),
    ('canceladas',  'Canceladas',   (0.86, 0.21, 0.27, 1)),
    ('no_asistidas','No asistidas', (1.0, 0.34, 0.13, 1)),
    ('total',       'Total',        (0.40, 0.23, 0.72, 1)),
]


def _stat_card(valor, etiqueta, color):
    card = MDCard(
        orientation='vertical',
        padding=dp(12),
        size_hint_y=None,
        height=dp(90),
        md_bg_color=color,
        radius=[12],
    )
    card.add_widget(MDLabel(
        text=str(valor),
        font_style='H4',
        halign='center',
        theme_text_color='Custom',
        text_color=(1, 1, 1, 1),
        adaptive_height=True,
    ))
    card.add_widget(MDLabel(
        text=etiqueta,
        font_style='Caption',
        halign='center',
        theme_text_color='Custom',
        text_color=(1, 1, 1, 1),
        adaptive_height=True,
    ))
    return card


def _reunion_card(reunion):
    color = COLORES_ESTADO.get(reunion.get('estado', ''), (0.95, 0.95, 0.95, 1))
    card = MDCard(
        orientation='vertical',
        padding=dp(10),
        size_hint_y=None,
        height=dp(80),
        md_bg_color=color,
        radius=[8],
    )
    card.add_widget(MDLabel(
        text=reunion['asunto'],
        font_style='Subtitle1',
        adaptive_height=True,
        shorten=True,
        shorten_from='right',
    ))
    info = f"{reunion['hora']}  •  {reunion['lugar'] or 'Sin lugar'}  •  {reunion['estado'].upper()}"
    card.add_widget(MDLabel(
        text=info,
        font_style='Caption',
        adaptive_height=True,
    ))
    return card


class DashboardScreen(MDScreen):
    def on_pre_enter(self):
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self.actualizar(), 0)

    def actualizar(self):
        app = App.get_running_app()
        db = app.db

        self.actualizar_perfil()

        grid = self.ids.stats_grid
        grid.clear_widgets()
        stats = db.stats_dashboard()
        for key, etiqueta, color in STAT_CONFIG:
            grid.add_widget(_stat_card(stats.get(key, 0), etiqueta, color))

        lista = self.ids.lista_hoy
        lista.clear_widgets()
        reuniones = db.reuniones_hoy()
        if reuniones:
            for r in reuniones:
                lista.add_widget(_reunion_card(r))
        else:
            lista.add_widget(MDLabel(
                text='No hay reuniones programadas para hoy.',
                halign='center',
                font_style='Body1',
                adaptive_height=True,
            ))

    def actualizar_perfil(self):
        import os
        config = cargar_config()
        self.ids.lbl_nombre.text = config.get('nombre', 'Usuario')
        foto = config.get('foto_perfil', '')
        self.ids.avatar_img.source = ''
        self.ids.avatar_img.source = foto if foto and os.path.exists(foto) else ''
