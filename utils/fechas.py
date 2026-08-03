# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Formato de fechas en español para mostrar en pantalla (las fechas se
siguen guardando/comparando en ISO 'YYYY-MM-DD' en toda la base de datos;
esto es solo para la presentación)."""

MESES_LARGO = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]
MESES_CORTO = [
    'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
    'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic',
]


def fecha_larga(fecha_iso):
    """'2026-08-05' -> '5 de Agosto, 2026'"""
    try:
        anio, mes, dia = fecha_iso.split('-')
        return f'{int(dia)} de {MESES_LARGO[int(mes) - 1].capitalize()}, {anio}'
    except Exception:
        return fecha_iso or ''


def fecha_corta(fecha_iso, hora=''):
    """'2026-08-05', '18:00' -> '5 Ago, 18:00h' (sin hora: '5 Ago')"""
    try:
        anio, mes, dia = fecha_iso.split('-')
        base = f'{int(dia)} {MESES_CORTO[int(mes) - 1]}'
        return f'{base}, {hora}h' if hora else base
    except Exception:
        return fecha_iso or ''
