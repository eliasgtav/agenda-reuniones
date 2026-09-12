# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Mixins compartidos entre pantallas (screens/*.py) para comportamiento que
antes se copiaba y pegaba igual en varios archivos."""
from kivy.clock import Clock
from kivy.core.window import Window


def _desvincular_hover(widget):
    """MDCard hereda FocusBehavior -> HoverBehavior (kivymd/uix/behaviors/
    hover_behavior.py), que en su __init__ hace
    `Window.bind(mouse_pos=self.on_mouse_update)` -- y no hay ningun
    __del__/on_parent/unbind en esa clase que lo deshaga. Quitar el widget
    del arbol (clear_widgets(), remove_widget()) no rompe esa atadura: el
    MDCard sigue vivo en memoria SOLO por esa referencia desde Window, y
    sigue recibiendo cada movimiento de mouse de la app para siempre.
    Listas que se reconstruyen en cada visita a la pantalla (Lista de
    Reuniones, Seguimiento de Acuerdos) acumulan mas y mas de estos
    "zombies" con cada navegacion -- confirmado midiendo tiempos reales:
    Seguimiento (crea 3 MDCard por fila via crear_tarjeta_acuerdo) paso de
    9s a 50s en 3 visitas seguidas; Lista (1 MDCard por fila) de 2s a 8s
    (2026-09-12). Hay que desatar `on_mouse_update` de Window a mano antes
    de soltar el widget, recorriendo tambien sus hijos (crear_tarjeta_acuerdo
    anida varios MDCard dentro de cada tarjeta)."""
    on_mouse_update = getattr(widget, 'on_mouse_update', None)
    if on_mouse_update is not None:
        Window.unbind(mouse_pos=on_mouse_update)
    for hijo in widget.children:
        _desvincular_hover(hijo)


def limpiar_lista(contenedor):
    """clear_widgets() de `contenedor` desatando primero el leak de
    HoverBehavior de cada hijo (ver _desvincular_hover). Usar esto en vez
    de contenedor.clear_widgets() a secas en cualquier lista que reconstruya
    MDCard repetidamente."""
    for hijo in list(contenedor.children):
        _desvincular_hover(hijo)
    contenedor.clear_widgets()


class ScrollArribaMixin:
    """Fuerza el MDScrollView de la pantalla (debe tener `id: scroll_view`
    en su regla kv) a quedar arriba del todo tras recargar contenido.

    Antes duplicado literal en 6 pantallas (dashboard, nueva_reunion,
    lista_reuniones, seguimiento, perfil, detalle_reunion) -- unificado
    aquí.

    Por qué reintentos programados en vez de una sola llamada: justo
    después de reconstruir el contenido (o en el primer render), el
    MDScrollView puede no haber terminado su propio layout todavía
    (`adaptive_height` calculando la altura real) -- fijar `scroll_y=1` una
    sola vez a veces no "pega" porque el contenido sigue creciendo después.
    Reintentar en varios delays cortos cubre eso sin enganchar eventos de
    layout más complejos.
    """
    _scroll_retry_events = None

    def _forzar_scroll_arriba(self):
        sv = self.ids.scroll_view

        def _reset(dt=None):
            sv.scroll_y = 1
            sv.update_from_scroll()

        _reset()
        self._scroll_retry_events = [
            Clock.schedule_once(_reset, delay)
            for delay in (0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0)
        ]

    def _cancelar_scroll_retries(self):
        for ev in (self._scroll_retry_events or []):
            ev.cancel()
        self._scroll_retry_events = None


class PaginacionMixin:
    """Scroll infinito genérico: primera página en cargar(), siguientes
    páginas al acercarse al final del MDScrollView (`id: scroll_view`).

    Antes duplicado literal entre lista_reuniones_screen.py y
    seguimiento_screen.py (mismos atributos `_offset`/`_hay_mas`/
    `_cargando_mas`, mismo `_on_scroll_y`, misma estructura de
    `cargar()`/`cargar_mas()` -- solo cambiaba qué método de `db` se
    llamaba). La pantalla que use este mixin debe:
      - Declarar `on_scroll_y: root._on_scroll_y(self.scroll_y)` en el
        MDScrollView de su regla kv.
      - Implementar `_fetch_pagina(self, limit, offset)` -> lista de filas.
      - Implementar `_agregar_item(self, item)` -> agrega un widget a su
        lista visible (MDBoxLayout de destino).
      - Llamar a `self._cargar_pagina(reset=True)` en su cargar() propio,
        después de limpiar los widgets/estado de filtro.
    """
    PAGE_SIZE = 40
    _offset = 0
    _hay_mas = True
    _cargando_mas = False

    def _cargar_pagina(self, reset):
        if reset:
            self._offset = 0
            self._hay_mas = True
        if not self._hay_mas:
            return []
        items = self._fetch_pagina(self.PAGE_SIZE, self._offset)
        for item in items:
            self._agregar_item(item)
        self._offset += len(items)
        self._hay_mas = len(items) == self.PAGE_SIZE
        return items

    def _on_scroll_y(self, valor):
        # scroll_y de MDScrollView: 1 = arriba del todo, 0 = abajo del todo.
        if valor <= 0.15:
            self.cargar_mas()

    def cargar_mas(self):
        if self._cargando_mas or not self._hay_mas:
            return
        self._cargando_mas = True
        self._cargar_pagina(reset=False)
        # Liberar el candado en el PROXIMO frame, no ahora mismo: on_scroll_y
        # se dispara varias veces por gesto y _cargar_pagina es sincrono, asi
        # que un solo flick hasta el final -- antes de que el layout recalcule
        # la altura con las 40 filas nuevas y suba scroll_y por encima de
        # 0.15 -- encadenaba 2-3 paginas de una. Con el reset diferido se
        # carga como mucho una pagina por frame.
        Clock.schedule_once(self._liberar_candado_paginacion, 0)

    def _liberar_candado_paginacion(self, dt):
        self._cargando_mas = False
