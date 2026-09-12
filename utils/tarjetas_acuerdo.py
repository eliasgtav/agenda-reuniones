# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Tarjeta de acuerdo/compromiso reutilizable (Detalle de reunión y
Seguimiento de Acuerdos): chip de prioridad, avatar con inicial del
responsable, fecha límite y checkbox de estado — mismo diseño en ambas
pantallas."""
from datetime import datetime

from kivy.metrics import dp
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton
from kivymd.uix.selectioncontrol import MDCheckbox

from utils.fechas import fecha_corta, fecha_larga

PRIORIDAD_LABELS = {'baja': 'Baja', 'media': 'Media', 'alta': 'Alta'}
_PRIORIDAD_CHIP = {'baja': 'BAJA PRIO.', 'media': 'MEDIA PRIO.', 'alta': 'ALTA PRIO.'}
PRIORIDAD_COLORES = {
    'baja':  (0.20, 0.55, 0.35, 1),
    'media': (0.85, 0.55, 0.10, 1),
    'alta':  (0.80, 0.20, 0.20, 1),
}

_AVATAR_COLORES = [
    (0.13, 0.40, 0.75, 1),
    (0.75, 0.35, 0.13, 1),
    (0.20, 0.55, 0.35, 1),
    (0.55, 0.25, 0.65, 1),
    (0.75, 0.45, 0.10, 1),
    (0.20, 0.45, 0.60, 1),
]


def _color_avatar(nombre):
    if not nombre:
        return (0.6, 0.6, 0.6, 1)
    return _AVATAR_COLORES[sum(ord(c) for c in nombre) % len(_AVATAR_COLORES)]


def _avatar_inicial(nombre, size=None):
    size = size or dp(34)
    circulo = MDCard(
        size_hint=(None, None),
        size=(size, size),
        radius=[size / 2],
        md_bg_color=_color_avatar(nombre),
    )
    circulo.add_widget(MDLabel(
        text=(nombre[:1].upper() if nombre else '?'),
        halign='center',
        valign='middle',
        text_size=(size, size),
        bold=True,
        theme_text_color='Custom',
        text_color=(1, 1, 1, 1),
    ))
    return circulo


def _chip(texto, color, width):
    chip = MDCard(
        size_hint=(None, None),
        size=(width, dp(22)),
        radius=[dp(11)],
        md_bg_color=color,
    )
    chip.add_widget(MDLabel(
        text=texto,
        font_style='Caption',
        bold=True,
        halign='center',
        valign='middle',
        text_size=(width, dp(22)),
        theme_text_color='Custom',
        text_color=(1, 1, 1, 1),
    ))
    return chip


def crear_tarjeta_acuerdo(ac, on_toggle_estado, on_ver_reunion=None, on_eliminar=None, on_editar=None, mostrar_reunion=False, numero=None):
    """Construye la tarjeta de un acuerdo/compromiso.

    ac: dict de la fila de la tabla `acuerdos` (+ `reunion_asunto` si viene
        de un JOIN, ver Database.listar_todos_acuerdos).
    on_toggle_estado(acuerdo_id, estaba_completado): cambia pendiente<->completado.
    on_ver_reunion(reunion_id) / on_eliminar(acuerdo_id): botones opcionales.
    on_editar(ac): botón opcional para abrir el acuerdo completo en edición.
    numero: si se da, antepone "N.- " al título (lista numerada en orden).
    """
    completado = ac.get('estado') == 'completado'
    hoy = datetime.now().strftime('%Y-%m-%d')
    plazo = ac.get('plazo', '')
    vencido = (not completado) and bool(plazo) and plazo < hoy

    if completado:
        estado_texto, estado_color = 'COMPLETADO', (0.20, 0.55, 0.20, 1)
    elif vencido:
        estado_texto, estado_color = 'VENCIDO', (0.80, 0.15, 0.15, 1)
    else:
        estado_texto, estado_color = 'PENDIENTE', (0.55, 0.55, 0.55, 1)

    prioridad = ac.get('prioridad', 'media')

    card = MDCard(
        orientation='vertical',
        padding=dp(12),
        spacing=dp(6),
        size_hint_y=None,
        adaptive_height=True,
        radius=[12],
        line_color=(0.85, 0.85, 0.85, 1),
        line_width=1,
        md_bg_color=(1, 1, 1, 1),
    )

    fila_chip = MDBoxLayout(adaptive_height=True)
    fila_chip.add_widget(_chip(
        _PRIORIDAD_CHIP.get(prioridad, 'MEDIA PRIO.'),
        PRIORIDAD_COLORES.get(prioridad, (0.6, 0.6, 0.6, 1)),
        dp(96),
    ))
    fila_chip.add_widget(MDBoxLayout())

    if mostrar_reunion and ac.get('reunion_asunto'):
        # Orden pedido: reunión primero, fecha debajo, chip de prioridad
        # debajo de la fecha -- y recién después el texto del acuerdo.
        # Un solo MDLabel con '\n' en vez de dos: cada MDLabel nuevo es una
        # textura que esta GPU (Intel HD 3000 via ANGLE, sin driver mas
        # nuevo -- ver commit de la sombra) tarda en subir; con ~14
        # tarjetas por pantalla, cada label de menos ahorra ~14 texturas.
        texto_reunion = f'REUNIÓN: {ac["reunion_asunto"].upper()}'
        if ac.get('reunion_fecha'):
            texto_reunion += f'\n{fecha_larga(ac["reunion_fecha"])}'
        card.add_widget(MDLabel(
            text=texto_reunion,
            font_style='Caption',
            bold=True,
            adaptive_height=True,
            theme_text_color='Secondary',
        ))
        card.add_widget(fila_chip)
    else:
        card.add_widget(fila_chip)

    texto_titulo = ac['texto'].upper()
    if numero:
        texto_titulo = f'{numero}.- {texto_titulo}'
    lbl_titulo = MDLabel(
        text=texto_titulo,
        font_style='Subtitle1',
        bold=True,
        adaptive_height=True,
        halign='justify',
        theme_text_color='Secondary' if completado else 'Primary',
    )
    lbl_titulo.bind(width=lambda inst, w: setattr(inst, 'text_size', (w, None)))
    card.add_widget(lbl_titulo)

    fila_datos = MDBoxLayout(adaptive_height=True, spacing=dp(10))

    resp_box = MDBoxLayout(spacing=dp(8), adaptive_height=True)
    if ac.get('responsable'):
        resp_box.add_widget(_avatar_inicial(ac['responsable']))
    # Antes 2 MDLabel (etiqueta "RESPONSABLE:" + nombre) -- fusionados en
    # uno solo con '\n' por la misma razon del label de reunion de arriba.
    resp_box.add_widget(MDLabel(
        text=f"RESPONSABLE:\n{(ac.get('responsable') or 'Sin asignar').upper()}",
        font_style='Caption', bold=True, adaptive_height=True,
        theme_text_color='Secondary',
    ))
    fila_datos.add_widget(resp_box)

    plazo_box = MDBoxLayout(spacing=dp(4), adaptive_height=True)
    plazo_box.add_widget(MDIcon(
        icon='clock-outline',
        size_hint=(None, None),
        size=(dp(16), dp(16)),
        theme_text_color='Secondary',
        font_size='16sp',
    ))
    # Antes fila de icono+etiqueta "FECHA LÍMITE:" y debajo un segundo
    # MDLabel con la fecha -- fusionados en uno solo junto al icono.
    plazo_box.add_widget(MDLabel(
        text=f"FECHA LÍMITE:\n{fecha_corta(plazo, ac.get('plazo_hora', '')) if plazo else 'Sin plazo'}",
        font_style='Caption', bold=True, adaptive_height=True,
        theme_text_color='Custom',
        text_color=PRIORIDAD_COLORES.get(prioridad, (0.2, 0.2, 0.2, 1)),
    ))
    fila_datos.add_widget(plazo_box)
    card.add_widget(fila_datos)

    fila_estado = MDBoxLayout(adaptive_height=True, spacing=dp(8))
    fila_estado.add_widget(MDBoxLayout())
    fila_estado.add_widget(_chip(estado_texto, estado_color, dp(104)))
    check = MDCheckbox(size_hint=(None, None), size=(dp(32), dp(32)), active=completado)
    check.bind(active=lambda inst, val: on_toggle_estado(ac['id'], completado))
    fila_estado.add_widget(check)
    card.add_widget(fila_estado)

    if on_ver_reunion or on_editar or on_eliminar:
        fila_btn = MDBoxLayout(adaptive_height=True, spacing=dp(8))
        if on_ver_reunion:
            btn = MDFlatButton(text='VER REUNIÓN', size_hint_x=None, width=dp(110))
            btn.bind(on_release=lambda _, r=ac['reunion_id']: on_ver_reunion(r))
            fila_btn.add_widget(btn)
        if on_editar:
            btn_editar = MDFlatButton(text='EDITAR', size_hint_x=None, width=dp(80))
            btn_editar.bind(on_release=lambda _, a=ac: on_editar(a))
            fila_btn.add_widget(btn_editar)
        if on_eliminar:
            btn2 = MDFlatButton(
                text='ELIMINAR', size_hint_x=None, width=dp(90),
                theme_text_color='Custom', text_color=(0.8, 0.1, 0.1, 1),
            )
            btn2.bind(on_release=lambda _, i=ac['id']: on_eliminar(i))
            fila_btn.add_widget(btn2)
        card.add_widget(fila_btn)

    return card
