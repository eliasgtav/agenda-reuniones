# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Diálogos reutilizables -- confirmar_eliminar() antes se repetía como una
construcción de MDDialog+botones casi idéntica en Lista de Reuniones y dos
veces en Detalle de Reunión (borrar archivo, borrar acuerdo)."""
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton


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
