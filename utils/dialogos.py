# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Diálogos reutilizables -- confirmar_eliminar() antes se repetía como una
construcción de MDDialog+botones casi idéntica en Lista de Reuniones y dos
veces en Detalle de Reunión (borrar archivo, borrar acuerdo)."""
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton


def mostrar_info(titulo, texto, boton='OK', on_cerrar=None):
    """Diálogo de un solo botón (info/error/aviso): título + texto + un
    botón que lo cierra. Antes esta misma construcción de MDDialog estaba
    copiada casi igual como _mostrar/_mostrar_info/_mostrar_error/
    _mostrar_ok en 6 pantallas distintas (45 usos en total entre todas).

    `on_cerrar()`, si se da, se llama justo después de cerrar el diálogo
    (p.ej. nueva_reunion_screen.py navega al dashboard al aceptar)."""
    dialog = None

    def _cerrar(_x):
        dialog.dismiss()
        if on_cerrar:
            on_cerrar()

    dialog = MDDialog(
        title=titulo,
        text=texto,
        buttons=[MDFlatButton(text=boton, on_release=_cerrar)],
    )
    dialog.open()
    return dialog


def confirmar_eliminar(titulo, texto, on_confirmar, texto_boton='ELIMINAR'):
    """Abre un diálogo CANCELAR / ELIMINAR (rojo). `on_confirmar()` se llama
    sin argumentos solo si el usuario confirma; el diálogo se cierra solo en
    ambos casos. Devuelve la instancia de MDDialog por si el llamador
    necesita guardarla (no hace falta para cerrarla, ya se maneja sola)."""
    dialog = None

    def _confirmar(_x):
        dialog.dismiss()
        on_confirmar()

    dialog = MDDialog(
        title=titulo,
        text=texto,
        buttons=[
            MDFlatButton(text='CANCELAR', on_release=lambda x: dialog.dismiss()),
            MDRaisedButton(
                text=texto_boton,
                md_bg_color=(0.8, 0.1, 0.1, 1),
                on_release=_confirmar,
            ),
        ],
    )
    dialog.open()
    return dialog


def abrir_selector_fecha(on_save):
    """Abre un MDDatePicker; `on_save(fecha_iso)` recibe la fecha elegida en
    formato ISO 'YYYY-MM-DD' (el que usa toda la BD) -- quien llama la usa
    tal cual para guardar, o la convierte a DD/MM/AAAA solo si va a
    mostrarla en un campo de texto editable (mismo formato que ya usaba el
    diálogo de "Nuevo acuerdo con plazo").

    Antes cada pantalla (Nueva Reunión, En Reunión, Reprogramar, Nuevo
    acuerdo con plazo) abría su propio MDDatePicker con el mismo
    picker.bind(on_save=...)/picker.open() -- y dos de ellas mostraban la
    fecha resultante como ISO crudo en pantalla ("2026-09-20") mientras la
    tercera la mostraba en DD/MM/AAAA para el mismo tipo de dato."""
    from kivymd.uix.pickers import MDDatePicker
    picker = MDDatePicker()
    picker.bind(on_save=lambda inst, val, *a: on_save(val.strftime('%Y-%m-%d')))
    picker.open()
    return picker


def abrir_selector_hora(on_save):
    """Abre un MDTimePicker; `on_save(texto)` recibe la hora en 'HH:MM'.

    _switch_input() fuerza el modo reloj de manecillas -- MDTimePicker no
    ofrece esa opción al crearse, solo llamando a este método ya con el
    picker abierto (de ahí el Clock.schedule_once en vez de un kwarg)."""
    from kivymd.uix.pickers import MDTimePicker
    from kivy.clock import Clock
    picker = MDTimePicker()
    picker.bind(on_save=lambda inst, val, *a: on_save(val.strftime('%H:%M')))
    picker.open()
    Clock.schedule_once(lambda dt: picker._switch_input(), 0.3)
    return picker
