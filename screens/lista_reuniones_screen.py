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
from utils.widgets import CampoOrtografico, BotonPlano
from utils.fechas import fecha_larga
from utils.abrir_archivo import abrir as abrir_archivo
from utils.mixins_pantalla import ScrollArribaMixin, PaginacionMixin, limpiar_lista
from utils.dialogos import confirmar_eliminar

Builder.load_string('''
<ListaReunionesScreen>:
    MDBoxLayout:
        orientation: 'vertical'
        padding: '8dp'
        spacing: '6dp'

        CampoOrtografico:
            id: busqueda_field
            hint_text: "Buscar por asunto o lugar..."
            mode: "rectangle"
            size_hint_y: None
            height: '48dp'
            on_text: root.on_busqueda(self.text)

        MDBoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: '96dp'
            spacing: '4dp'
            id: filtros_bar

        MDBoxLayout:
            size_hint_y: None
            height: '40dp'

            BotonPlano:
                text: "Exportar a Excel"
                pos_hint: {"center_x": .5}
                on_release: root.exportar('excel')
                md_bg_color: 0.40, 0.40, 0.40, 1

        MDScrollView:
            id: scroll_view
            on_scroll_y: root._on_scroll_y(self.scroll_y)
            MDBoxLayout:
                id: lista_reuniones
                orientation: 'vertical'
                adaptive_height: True
                spacing: '6dp'
                padding: [0, '4dp']
''')

FILTROS = [
    ('todas',       'Todas',        (0.40, 0.40, 0.40, 1)),
    ('hoy',         'Hoy',          (0.13, 0.40, 0.75, 1)),
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


class ListaReunionesScreen(ScrollArribaMixin, PaginacionMixin, MDScreen):
    _filtro_activo = 'todas'
    _busqueda = ''
    _load_event = None

    def on_pre_enter(self):
        from kivy.clock import Clock
        def _init(dt):
            self._busqueda = ''
            self.ids.busqueda_field.text = ''
            self._construir_filtros()
            self.cargar()
        self._load_event = Clock.schedule_once(_init, 0)

    def on_leave(self):
        if self._load_event:
            self._load_event.cancel()
            self._load_event = None
        # El rebote de busqueda (0.4s) puede seguir pendiente al salir: sin
        # esto, _busqueda_cb disparaba cargar() -- clear_widgets + reconstruir
        # la lista + 8 eventos de scroll -- sobre una pantalla que ya no se ve.
        Clock.unschedule(self._busqueda_cb)
        self._cancelar_scroll_retries()

    def _construir_filtros(self):
        bar = self.ids.filtros_bar
        bar.clear_widgets()
        mitad = len(FILTROS) // 2
        for fila_filtros in (FILTROS[:mitad], FILTROS[mitad:]):
            fila = MDBoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
            for clave, etiqueta, color in fila_filtros:
                btn = BotonPlano(
                    text=etiqueta,
                    md_bg_color=color,
                    size_hint=(1, 1),
                    _radius=dp(14),
                )
                btn.bind(on_release=lambda _, k=clave: self.filtrar(k))
                fila.add_widget(btn)
            bar.add_widget(fila)

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
        # Trae solo la primera pagina (PantallaPaginacionMixin.PAGE_SIZE) --
        # con miles de reuniones guardadas, traer y dibujar la tabla
        # completa de una vez se sentia lento (medido con
        # scripts/benchmark_carga.py). El resto se agrega via cargar_mas()
        # (heredado del mixin) al acercarse al final del scroll.
        lista = self.ids.lista_reuniones
        limpiar_lista(lista)
        items = self._cargar_pagina(reset=True)
        if not items:
            lista.add_widget(MDLabel(
                text='Sin resultados.',
                halign='center',
                adaptive_height=True,
                padding=[0, dp(20)],
            ))
        self._forzar_scroll_arriba()

    def _fetch_pagina(self, limit, offset):
        app = App.get_running_app()
        return app.db.listar_reuniones(
            estado=self._filtro_activo,
            busqueda=self._busqueda or None,
            limit=limit,
            offset=offset,
        )

    def _agregar_item(self, reunion):
        self.ids.lista_reuniones.add_widget(self._crear_card(reunion))

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

        info = f"{fecha_larga(reunion['fecha'])}  {reunion['hora']}  —  {reunion['lugar'] or 'Sin lugar'}"
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
        app._PARENT_SCREEN['detalle_reunion'] = 'lista_reuniones'
        app.go_to('detalle_reunion')

    def _confirmar_borrar(self, reunion_id):
        app = App.get_running_app()

        def _borrar():
            app.db.eliminar_reunion(reunion_id)
            self.cargar()

        confirmar_eliminar(
            'Confirmar eliminación',
            '¿Deseas eliminar esta reunión permanentemente?',
            _borrar,
        )

    def exportar(self, formato):
        app = App.get_running_app()
        reuniones = app.db.listar_reuniones(
            estado=self._filtro_activo,
            busqueda=self._busqueda or None,
        )
        ruta = exportar_excel(reuniones, app.db)
        if not ruta:
            dialog = MDDialog(
                title='Error',
                text='Error al exportar. Verifique que openpyxl esté instalado.',
                buttons=[MDFlatButton(text='OK', on_release=lambda x: dialog.dismiss())],
            )
            dialog.open()
            return

        def _abrir(_x):
            import os
            dialog.dismiss()
            abrir_archivo(ruta, os.path.basename(ruta), on_error=lambda m: self._mostrar_error_apertura(m))

        dialog = MDDialog(
            title='Exportación completada',
            text=f'Archivo guardado en Descargas:\n{ruta}\n\n¿Deseas abrirlo?',
            buttons=[
                MDFlatButton(text='NO', on_release=lambda x: dialog.dismiss()),
                MDRaisedButton(text='ABRIR', on_release=_abrir),
            ],
        )
        dialog.open()

    def _mostrar_error_apertura(self, mensaje):
        dialog = MDDialog(
            title='Aviso',
            text=mensaje,
            buttons=[MDFlatButton(text='OK', on_release=lambda x: dialog.dismiss())],
        )
        dialog.open()
