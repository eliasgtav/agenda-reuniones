# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Widget que recorta a sus hijos dentro de un circulo.

MDCard.radius solo redondea su propio fondo (el rectangulo que dibuja),
no recorta a los widgets hijos -- un Image adentro se sigue dibujando
como rectangulo completo, con las esquinas asomando fuera del circulo.
Aqui se usa el stencil buffer de Kivy para recortar de verdad."""
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Ellipse, StencilPush, StencilUse, StencilUnUse, StencilPop


class RecorteCircular(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            StencilPush()
            self._mascara1 = Ellipse(pos=self.pos, size=self.size)
            StencilUse()
        with self.canvas.after:
            StencilUnUse()
            self._mascara2 = Ellipse(pos=self.pos, size=self.size)
            StencilPop()
        self.bind(pos=self._actualizar_mascara, size=self._actualizar_mascara)

    def _actualizar_mascara(self, *_a):
        self._mascara1.pos = self._mascara2.pos = self.pos
        self._mascara1.size = self._mascara2.size = self.size
