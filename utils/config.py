# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
import json
import os

_CONFIG_PATH = os.path.join(os.path.expanduser('~'), 'agenda_config.json')

_DEFAULTS = {
    'nombre': 'Usuario',
    'foto_perfil': '',
}


def cargar():
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {**_DEFAULTS, **data}
        except Exception:
            pass
    return dict(_DEFAULTS)


def guardar(config):
    with open(_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
