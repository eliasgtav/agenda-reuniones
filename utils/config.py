# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
import base64
import hashlib
import json
import os
from kivy.utils import platform

_DEFAULTS = {
    'nombre': 'Usuario',
    'foto_perfil': '',
    'sms_auto_respuesta': 'Estoy en una reunión, te devuelvo la llamada en cuanto termine.',
}

# La contraseña de aplicación de correo NUNCA se guarda en texto plano en
# agenda_config.json (antes sí, cualquiera que abriera el archivo la veía
# directo). Se cifra con XOR+base64 usando una clave fija derivada por
# SHA-256 -- no protege contra alguien que lea el código fuente de esta app,
# pero sí evita que el password quede legible a simple vista si el archivo
# de config se filtra, se comparte por error, o lo abre otra app en el
# dispositivo. En disco vive bajo la clave 'correo_password_enc'; en memoria
# (el dict que devuelve cargar()) sigue accesible como 'correo_password' en
# claro, igual que antes, para no tocar el resto de la app.
_CAMPO_PASSWORD = 'correo_password'
_CAMPO_PASSWORD_CIFRADO = 'correo_password_enc'
_CIFRADO_SEMILLA = 'AgendaReuniones-EliasGaytanAlvino-config-v1'


def _clave_cifrado():
    return hashlib.sha256(_CIFRADO_SEMILLA.encode('utf-8')).digest()


def _cifrar_password(texto):
    if not texto:
        return ''
    clave = _clave_cifrado()
    datos = texto.encode('utf-8')
    cifrado = bytes(b ^ clave[i % len(clave)] for i, b in enumerate(datos))
    return base64.b64encode(cifrado).decode('ascii')


def _descifrar_password(texto_cifrado):
    if not texto_cifrado:
        return ''
    try:
        clave = _clave_cifrado()
        datos = base64.b64decode(texto_cifrado.encode('ascii'))
        plano = bytes(b ^ clave[i % len(clave)] for i, b in enumerate(datos))
        return plano.decode('utf-8')
    except Exception:
        return ''


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
                config = {**_DEFAULTS, **data}
                if _CAMPO_PASSWORD_CIFRADO in data:
                    config[_CAMPO_PASSWORD] = _descifrar_password(data[_CAMPO_PASSWORD_CIFRADO])
                config.pop(_CAMPO_PASSWORD_CIFRADO, None)
                # Si no había 'correo_password_enc', config[_CAMPO_PASSWORD] ya
                # quedó con el valor en texto plano de instalaciones previas a
                # este fix -- se migra a cifrado solo con leerlo, en el
                # siguiente guardar() (cualquiera, no hace falta que sea el de
                # Perfil) ya se escribe cifrado.
                return config
        except Exception:
            # Un JSON corrupto (escritura interrumpida, disco lleno, encoding
            # raro) antes devolvía los defaults en silencio -- el usuario
            # perdía correo/contraseña/mensaje SMS sin ningún aviso ni forma
            # de recuperarlo. Se guarda el archivo dañado aparte (con
            # timestamp, nunca sobrescribe un backup previo) antes de caer a
            # los defaults, para poder inspeccionarlo/recuperarlo a mano.
            try:
                import shutil
                from datetime import datetime
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                shutil.copy2(ruta, f'{ruta}.corrupto_{ts}')
            except Exception:
                pass
    return dict(_DEFAULTS)


def guardar(config):
    data = dict(config)
    password = data.pop(_CAMPO_PASSWORD, '')
    data[_CAMPO_PASSWORD_CIFRADO] = _cifrar_password(password)
    ruta = _config_path()
    # Escritura atomica (temp + replace): si el proceso se interrumpe a
    # mitad de camino (disco lleno, app forzada a cerrar), agenda_config.json
    # se queda con el contenido anterior completo en vez de un JSON truncado
    # a medio escribir. La excepcion (OSError si falla el disco/permiso de
    # Android) se deja propagar -- quien llama a guardar() debe atraparla y
    # avisar al usuario, no se traga en silencio aqui.
    tmp = f'{ruta}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ruta)
