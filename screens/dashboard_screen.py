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
        id: scroll_view
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
                    radius: [dp(32)]
                    md_bg_color: app.theme_cls.primary_color

                    FloatLayout:
                        size_hint: 1, 1

                        Image:
                            id: avatar_img
                            source: ""
                            allow_stretch: True
                            keep_ratio: False
                            size_hint: 1, 1
                            pos_hint: {"x": 0, "y": 0}

                        MDLabel:
                            id: avatar_iniciales_lbl
                            text: ""
                            font_style: "H6"
                            bold: False
                            halign: "center"
                            valign: "middle"
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                            size_hint: 1, 1
                            pos_hint: {"x": 0, "y": 0}
                            text_size: self.size

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

            MDRaisedButton:
                text: "VER TODAS LAS REUNIONES"
                pos_hint: {'center_x': .5}
                on_release: app.go_to('lista_reuniones')

            MDRaisedButton:
                id: btn_seguimiento
                text: "SEGUIMIENTO DE ACUERDOS"
                pos_hint: {'center_x': .5}
                md_bg_color: 0.13, 0.40, 0.75, 1
                on_release: app.go_to('seguimiento')

            MDLabel:
                text: "© Elías Gaytan Alvino"
                font_style: "Caption"
                halign: "center"
                adaptive_height: True
                padding: [0, '16dp']
''')

STAT_CONFIG = [
    ('hoy',         'Hoy',          (0.13, 0.40, 0.75, 1)),
    ('pendientes',  'Pendientes',   (1.0, 0.75, 0.0, 1)),
    ('realizadas',  'Realizadas',   (0.18, 0.65, 0.28, 1)),
    ('canceladas',  'Canceladas',   (0.86, 0.21, 0.27, 1)),
    ('no_asistidas','No asistidas', (1.0, 0.34, 0.13, 1)),
    ('total',       'Total',        (0.40, 0.23, 0.72, 1)),
]


def _stat_card(valor, etiqueta, color, on_release=None):
    card = MDCard(
        orientation='vertical',
        padding=dp(12),
        size_hint_y=None,
        height=dp(90),
        md_bg_color=color,
        radius=[12],
        ripple_behavior=on_release is not None,
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
    if on_release is not None:
        card.bind(on_release=on_release)
    return card


class DashboardScreen(MDScreen):
    _scroll_retry_events = None
    _load_event = None

    def on_pre_enter(self):
        from kivy.clock import Clock
        self._load_event = Clock.schedule_once(lambda dt: self.actualizar(), 0)

    def on_leave(self):
        # Cancela la carga y los reintentos pendientes: si siguen
        # disparando despues de salir de la pantalla, fuerzan una
        # reconstruccion/redibujo justo mientras SlideTransition anima la
        # salida, y se ve como un destello/salto de esta pantalla al
        # cambiar a otra.
        if self._load_event:
            self._load_event.cancel()
            self._load_event = None
        for ev in (self._scroll_retry_events or []):
            ev.cancel()
        self._scroll_retry_events = None

    def actualizar(self):
        app = App.get_running_app()
        db = app.db

        self.actualizar_perfil()

        grid = self.ids.stats_grid
        grid.clear_widgets()
        stats = db.stats_dashboard()
        for key, etiqueta, color in STAT_CONFIG:
            on_release = self._ir_a_hoy if key == 'hoy' else None
            grid.add_widget(_stat_card(stats.get(key, 0), etiqueta, color, on_release))

        activos = db.contar_acuerdos_activos()
        self.ids.btn_seguimiento.text = (
            f'SEGUIMIENTO DE ACUERDOS ({activos})' if activos else 'SEGUIMIENTO DE ACUERDOS'
        )

        self._forzar_scroll_arriba()

    def _ir_a_hoy(self, *args):
        app = App.get_running_app()
        lista_screen = app.root.ids.sm.get_screen('lista_reuniones')
        lista_screen._filtro_activo = 'hoy'
        app.go_to('lista_reuniones')

    def _forzar_scroll_arriba(self):
        # El contenido (adaptive_height) puede tardar varios cuadros en
        # terminar de medirse en Android, y mientras tanto el MDScrollView
        # puede quedar "scrolleado" al fondo -- aunque scroll_y ya reporte
        # 1, el area dibujada no siempre coincide (condicion de carrera, no
        # se arregla con un solo intento a tiempo fijo). Se reintenta varias
        # veces durante el primer segundo y se fuerza update_from_scroll()
        # para que el redibujado coincida con la propiedad.
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

    def actualizar_perfil(self):
        import os
        config = cargar_config()
        self.ids.lbl_nombre.text = config.get('nombre', 'Usuario')
        foto = config.get('foto_perfil', '')
        existe = bool(foto) and os.path.exists(foto)
        self.ids.avatar_img.source = ''
        self.ids.avatar_img.source = foto if existe else ''
        # Sin foto, Image(source='') igual pinta un rectángulo blanco sólido
        # (Kivy dibuja el Rectangle del canvas del Image con el Color blanco
        # por defecto cuando no hay texture) encima del MDCard circular --
        # se ve como un cuadrado blanco tapando el círculo de fondo. Se
        # oculta el Image cuando no hay foto real y en su lugar se muestran
        # las iniciales, mismo patrón que perfil_screen.py.
        self.ids.avatar_img.opacity = 1 if existe else 0
        self.ids.avatar_iniciales_lbl.opacity = 0 if existe else 1
        nombres = config.get('nombres', '')
        apellidos = config.get('apellidos', '')
        self.ids.avatar_iniciales_lbl.text = (nombres[:1] + apellidos[:1]).upper()
