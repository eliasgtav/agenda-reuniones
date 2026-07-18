# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
from kivy.lang import Builder
from kivy.app import App
from kivy.metrics import dp
from kivy.clock import Clock
from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from utils.exportar import exportar_excel

Builder.load_string('''
<ListaReunionesScreen>:
    MDBoxLayout:
        orientation: 'vertical'
        padding: '8dp'
        spacing: '6dp'

        MDTextField:
            id: busqueda_field
            hint_text: "Buscar por asunto o lugar..."
            mode: "rectangle"
            size_hint_y: None
            height: '48dp'
            on_text: root.on_busqueda(self.text)

        MDBoxLayout:
            size_hint_y: None
            height: '40dp'
            spacing: '4dp'
            id: filtros_bar

        MDBoxLayout:
            size_hint_y: None
            height: '40dp'
            spacing: '8dp'

            MDRaisedButton:
                text: "Exportar a Excel"
                on_release: root.exportar('excel')
                md_bg_color: 0.13, 0.40, 0.75, 1

        MDScrollView:
            id: scroll_view
            MDBoxLayout:
                id: lista_reuniones
                orientation: 'vertical'
                adaptive_height: True
                spacing: '6dp'
                padding: [0, '4dp']
''')

FILTROS = [
    ('todas',       'Todas',        (0.40, 0.40, 0.40, 1)),
    ('pendiente',   'Pendientes',   (0.80, 0.65, 0.0,  1)),
    ('realizada',   'Realizadas',   (0.13, 0.55, 0.13, 1)),
    ('cancelada',   'Canceladas',   (0.80, 0.13, 0.13, 1)),
    ('no_asistida', 'No asistidas', (0.90, 0.40, 0.13, 1)),
]

COLORES_ESTADO = {
    'pendiente':   (1.00, 0.98, 0.77, 1),
    'realizada':   (0.78, 0.90, 0.79, 1),
    'cancelada':   (1.00, 0.80, 0.82, 1),
    'no_asistida': (1.00, 0.88, 0.70, 1),
}


class ListaReunionesScreen(MDScreen):
    _filtro_activo = 'todas'
    _busqueda = ''
    _dialog = None

    def on_pre_enter(self):
        from kivy.clock import Clock
        def _init(dt):
            self._busqueda = ''
            self.ids.busqueda_field.text = ''
            self._construir_filtros()
            self.cargar()
        Clock.schedule_once(_init, 0)

    def _construir_filtros(self):
        bar = self.ids.filtros_bar
        bar.clear_widgets()
        for clave, etiqueta, color in FILTROS:
            btn = MDRaisedButton(
                text=etiqueta,
                md_bg_color=color,
                size_hint_x=None,
                width=dp(90),
            )
            btn.bind(on_release=lambda _, k=clave: self.filtrar(k))
            bar.add_widget(btn)

    def filtrar(self, estado):
        self._filtro_activo = estado
        self._busqueda = ''
        self.ids.busqueda_field.text = ''
        self.cargar()

    def on_busqueda(self, texto):
        self._busqueda = texto.strip()
        Clock.unschedule(self._busqueda_cb)
        Clock.schedule_once(self._busqueda_cb, 0.4)

    def _busqueda_cb(self, *args):
        self.cargar()

    def cargar(self):
        app = App.get_running_app()
        reuniones = app.db.listar_reuniones(
            estado=self._filtro_activo,
            busqueda=self._busqueda or None,
        )
        lista = self.ids.lista_reuniones
        lista.clear_widgets()
        if not reuniones:
            lista.add_widget(MDLabel(
                text='Sin resultados.',
                halign='center',
                adaptive_height=True,
                padding=[0, dp(20)],
            ))
            self._forzar_scroll_arriba()
            return
        for r in reuniones:
            lista.add_widget(self._crear_card(r))
        self._forzar_scroll_arriba()

    def _forzar_scroll_arriba(self):
        # Ver nota en dashboard_screen.py: el MDScrollView puede quedar
        # "scrolleado" al fondo si el contenido (adaptive_height) todavía
        # no llega a su tamaño final cuando se calcula el rango de scroll.
        from kivy.clock import Clock
        self.ids.scroll_view.scroll_y = 1
        Clock.schedule_once(lambda dt: setattr(self.ids.scroll_view, 'scroll_y', 1), 0)

    def _crear_card(self, reunion):
        color = COLORES_ESTADO.get(reunion['estado'], (0.95, 0.95, 0.95, 1))
        card = MDCard(
            orientation='vertical',
            padding=dp(10),
            size_hint_y=None,
            height=dp(90),
            md_bg_color=color,
            radius=[8],
            ripple_behavior=True,
        )

        fila1 = MDBoxLayout(adaptive_height=True)
        fila1.add_widget(MDLabel(
            text=reunion['asunto'],
            font_style='Subtitle1',
            adaptive_height=True,
            shorten=True,
            shorten_from='right',
        ))
        estado_lbl = MDLabel(
            text=reunion['estado'].upper(),
            font_style='Caption',
            halign='right',
            adaptive_height=True,
            size_hint_x=None,
            width=dp(90),
        )
        fila1.add_widget(estado_lbl)
        card.add_widget(fila1)

        info = f"{reunion['fecha']}  {reunion['hora']}  —  {reunion['lugar'] or 'Sin lugar'}"
        card.add_widget(MDLabel(
            text=info,
            font_style='Caption',
            adaptive_height=True,
        ))

        fila_btns = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        rid = reunion['id']

        btn_ver = MDFlatButton(text='VER', size_hint_x=None, width=dp(60))
        btn_ver.bind(on_release=lambda _, r=rid: self._abrir_detalle(r))

        btn_del = MDFlatButton(
            text='BORRAR',
            size_hint_x=None,
            width=dp(70),
            theme_text_color='Custom',
            text_color=(0.8, 0.1, 0.1, 1),
        )
        btn_del.bind(on_release=lambda _, r=rid: self._confirmar_borrar(r))

        fila_btns.add_widget(btn_ver)
        fila_btns.add_widget(btn_del)
        card.add_widget(fila_btns)

        return card

    def _abrir_detalle(self, reunion_id):
        app = App.get_running_app()
        app.reunion_activa_id = reunion_id
        app.go_to('detalle_reunion')

    def _confirmar_borrar(self, reunion_id):
        app = App.get_running_app()

        def _borrar(_):
            app.db.eliminar_reunion(reunion_id)
            self._dialog.dismiss()
            self.cargar()

        self._dialog = MDDialog(
            title='Confirmar eliminación',
            text='¿Deseas eliminar esta reunión permanentemente?',
            buttons=[
                MDFlatButton(text='CANCELAR', on_release=lambda x: self._dialog.dismiss()),
                MDRaisedButton(
                    text='ELIMINAR',
                    md_bg_color=(0.8, 0.1, 0.1, 1),
                    on_release=_borrar,
                ),
            ],
        )
        self._dialog.open()

    def exportar(self, formato):
        app = App.get_running_app()
        reuniones = app.db.listar_reuniones(
            estado=self._filtro_activo,
            busqueda=self._busqueda or None,
        )
        ruta = exportar_excel(reuniones, app.db)
        msg = f'Archivo guardado en Descargas:\n{ruta}' if ruta else 'Error al exportar. Verifique que openpyxl esté instalado.'
        dialog = MDDialog(
            title='Exportación completada' if ruta else 'Error',
            text=msg,
            buttons=[MDFlatButton(text='OK', on_release=lambda x: dialog.dismiss())],
        )
        dialog.open()
