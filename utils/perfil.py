# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Ayudas compartidas para mostrar la identidad del usuario. El cálculo de
iniciales (nombres + apellidos -> 2 letras mayúsculas) estaba duplicado
literal en screens/login_screen.py y screens/perfil_screen.py (mismo
formato exacto), y con la misma fórmula en screens/dashboard_screen.py."""


def iniciales_de(nombres, apellidos):
    return (nombres[:1] + apellidos[:1]).upper()
