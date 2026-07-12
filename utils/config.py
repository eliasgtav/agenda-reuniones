# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
import json
import os
from kivy.utils import platform

_DEFAULTS = {
    'nombre': 'Usuario',
    'foto_perfil': '',
}


def _config_path():
    # os.path.expanduser('~') no es fiable en Android (puede no haber HOME
    # y devolver la ruta sin expandir): usar el directorio de datos de la
    # app, igual que database.py._get_db_path().
    base = None
    if platform == 'android':
        try:
            from kivy.app import App
            app = App.get_running_app()
            base = app.user_data_dir if app else None
        except Exception:
            base = None
        if not base:
            try:
                from android.storage import app_storage_path
                base = app_storage_path()
            except Exception:
                base = None
    if not base:
        base = os.path.expanduser('~')
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        base = os.path.expanduser('~')
    return os.path.join(base, 'agenda_config.json')


def cargar():
    ruta = _config_path()
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {**_DEFAULTS, **data}
        except Exception:
            pass
    return dict(_DEFAULTS)


def guardar(config):
    with open(_config_path(), 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
