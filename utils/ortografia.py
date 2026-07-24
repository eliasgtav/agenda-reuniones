# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Corrector ortográfico compartido (español). Un solo diccionario cargado
una vez en segundo plano y reusado por todos los campos de texto, en vez de
uno por campo (parsear el diccionario es lo costoso, no revisar palabras)."""
import re
import threading

_LARGO_MINIMO = 3
_MAX_SUGERENCIAS = 3
_PALABRA_VALIDA = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ]+$")

_spell = None
_cargando = False
_lock = threading.Lock()


def precargar():
    """Lanza la carga del diccionario en un hilo aparte. Llamar una vez al
    arrancar la app (main.py::on_start) para que ya esté listo cuando el
    usuario empiece a escribir. Es segura de llamar más de una vez."""
    global _cargando
    with _lock:
        if _spell is not None or _cargando:
            return
        _cargando = True
    threading.Thread(target=_cargar, daemon=True).start()


def _cargar():
    global _spell, _cargando
    try:
        from spellchecker import SpellChecker
        corrector = SpellChecker(language='es')
    except Exception:
        corrector = None
    with _lock:
        _spell = corrector if corrector is not None else False
        _cargando = False


def sugerencias(palabra):
    """Devuelve hasta 3 sugerencias si `palabra` está mal escrita, o una
    lista vacía si está bien, es muy corta, no es un corrector aún
    disponible, o no es una palabra "revisable" (contiene números,
    signos, etc. — nombres de archivo, URLs, correos no aplican)."""
    if not palabra or len(palabra) < _LARGO_MINIMO or not _PALABRA_VALIDA.match(palabra):
        return []
    with _lock:
        corrector = _spell
    if not corrector:
        precargar()
        return []
    minuscula = palabra.lower()
    if minuscula not in corrector.unknown([minuscula]):
        return []
    candidatas = corrector.candidates(minuscula) or set()
    candidatas.discard(minuscula)
    ordenadas = sorted(candidatas, key=lambda w: -corrector.word_frequency[w])
    return ordenadas[:_MAX_SUGERENCIAS]
