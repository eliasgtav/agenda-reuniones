# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Las notas de una reunión pueden traer, al final, un bloque de acuerdos
capturados en vivo desde la pantalla "En Reunión", pegado tras el marcador
MARCADOR. Antes cada lugar que necesitaba separar ambas partes (En Reunión,
utils/email_sender.py) repetía su propio `'=== ACUERDOS ===' in notas` +
`split()` -- centralizado aquí para no duplicarlo."""

MARCADOR = '=== ACUERDOS ==='


def separar(notas):
    """Devuelve (notas_sin_bloque_acuerdos, bloque_acuerdos). Ambos ya vienen
    con `.strip()` aplicado; `bloque_acuerdos` es '' si no hay marcador."""
    notas = notas or ''
    if MARCADOR not in notas:
        return notas.strip(), ''
    antes, despues = notas.split(MARCADOR, 1)
    return antes.strip(), despues.strip()
