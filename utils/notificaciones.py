# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
import threading
from datetime import datetime, timedelta
from utils.config import cargar as cargar_config


def _minutos_para_reunion(fecha_str, hora_str):
    try:
        dt_reunion = datetime.strptime(f'{fecha_str} {hora_str}', '%Y-%m-%d %H:%M')
        return (dt_reunion - datetime.now()).total_seconds() / 60
    except Exception:
        return None


def _limpiar_acentos(texto):
    import unicodedata
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )


_FONETIKA = {
    # Helena TTS lee "Gay" como inglés → usar "Gai" (diptongo español)
    'gaytan': 'gaitan',
}


def _corregir_pronunciacion(texto):
    import re
    for mal, bien in _FONETIKA.items():
        texto = re.sub(re.escape(mal), bien, texto, flags=re.IGNORECASE)
    return texto


_engine_voz = None
_engine_voz_ok = None  # None: no probado aun, True: sirve, False: fallo permanente (usar plyer.tts)
_engine_voz_lock = threading.Lock()


def _obtener_engine_voz():
    """pyttsx3.init() + recorrer engine.getProperty('voices') buscando la
    voz en español tarda ~5s (medido) -- antes se repetia esto en CADA
    alerta de voz, asi que 2-3 avisos seguidos en el mismo tick de
    verificar_alertas() (p.ej. varios acuerdos venciendo el mismo dia)
    encadenaban ese arranque completo una vez por cada uno. El motor se
    crea una sola vez y se reusa; si falla una vez se recuerda para no
    reintentar un import/init lento que ya se sabe que no sirve en esta
    plataforma (p.ej. Android, donde se cae a plyer.tts siempre)."""
    global _engine_voz, _engine_voz_ok
    if _engine_voz_ok is False:
        return None
    if _engine_voz is not None:
        return _engine_voz
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty('rate', 130)
    for v in engine.getProperty('voices'):
        if 'ES' in v.id or 'Spanish' in v.name:
            engine.setProperty('voice', v.id)
            break
    _engine_voz = engine
    _engine_voz_ok = True
    return _engine_voz


def _hablar(texto):
    def _run():
        # El lock serializa el uso del motor entre hilos de distintas
        # alertas -- pyttsx3/SAPI no es seguro para usarse desde varios
        # hilos a la vez (confirmado: engines concurrentes de este mismo
        # motor podian colgar el proceso en pruebas de escritorio).
        with _engine_voz_lock:
            try:
                engine = _obtener_engine_voz()
                if engine is None:
                    raise RuntimeError('motor de voz no disponible')
                engine.say(_corregir_pronunciacion(_limpiar_acentos(texto)))
                engine.runAndWait()
            except Exception:
                global _engine_voz, _engine_voz_ok
                _engine_voz = None
                _engine_voz_ok = False
                try:
                    from plyer import tts
                    tts.speak(texto)
                except Exception:
                    pass
    threading.Thread(target=_run, daemon=True).start()


def _notificar(titulo, mensaje):
    try:
        from plyer import notification
        notification.notify(
            title=titulo,
            message=mensaje,
            app_name='Agenda de Reuniones',
            timeout=15,
        )
    except Exception:
        pass


def _saludo_usuario():
    partes_nombre = cargar_config().get('nombres', '').split()
    primer_nombre = partes_nombre[0] if partes_nombre else ''
    return f'{primer_nombre}, ' if primer_nombre else ''


def _avisar(titulo_push, msg_push, texto_voz):
    # Push y voz siempre van juntos en este modulo -- nunca uno sin el otro.
    _notificar(titulo_push, msg_push)
    _hablar(texto_voz)


UMBRALES = {
    '30min': (5, 15),
    '1hora': (10, 20),
    '1dia':  (25, 35),
}

MENSAJES = {
    '30min': 'en 10 minutos',
    '1hora': 'en 15 minutos',
    '1dia':  'en 30 minutos',
}


class NotificacionesManager:
    def __init__(self, db):
        self.db = db

    def verificar_alertas(self, *args):
        # main.py llama a esto cada 60s sin parar mientras la app este
        # abierta -- _saludo_usuario() hace un cargar_config() (leer +
        # desencriptar agenda_config.json de disco), asi que solo vale la
        # pena calcularlo la primera vez que de verdad hay algo que avisar
        # en este tick, no en cada uno aunque no haya alertas pendientes.
        saludo_cache = {}

        def saludo():
            if 'v' not in saludo_cache:
                saludo_cache['v'] = _saludo_usuario()
            return saludo_cache['v']

        for alerta in self.db.alertas_pendientes():
            minutos = _minutos_para_reunion(alerta['fecha'], alerta['hora'])
            if minutos is None:
                continue
            tipo = alerta['tipo']
            if tipo not in UMBRALES:
                continue
            lo, hi = UMBRALES[tipo]
            if lo <= minutos <= hi:
                asunto = alerta['asunto']
                cuando = MENSAJES[tipo]
                _avisar(
                    f'Reunión próxima — {cuando}',
                    f'{asunto} ({alerta["hora"]}) — {alerta.get("lugar","")}',
                    f'{saludo()}tiene una reunión {cuando}. Asunto: {asunto}.',
                )
                self.db.marcar_alerta_enviada(alerta['id'])
        self.verificar_plazos_acuerdos()

    def verificar_plazos_acuerdos(self):
        # Cada acuerdo avisa hasta 3 veces conforme se acerca su plazo
        # (manana -> hoy -> vencido), nunca la misma categoria dos veces --
        # antes se marcaba "ya avisado" tras la PRIMERA notificacion sin
        # importar cual, asi que un acuerdo que avisaba "vence manana" nunca
        # volvia a avisar cuando de verdad vencia. `ultima_alerta` guarda que
        # categoria fue la ultima notificada; "vencido" es terminal.
        from datetime import datetime
        hoy = datetime.now().strftime('%Y-%m-%d')
        saludo_cache = {}

        def saludo():
            if 'v' not in saludo_cache:
                saludo_cache['v'] = _saludo_usuario()
            return saludo_cache['v']

        for acuerdo in self.db.acuerdos_con_plazo_pendientes():
            plazo = acuerdo['plazo']
            texto = acuerdo['texto']
            reunion = acuerdo['reunion_asunto']
            responsable = acuerdo.get('responsable', '')
            quien = f' asignado a {responsable}' if responsable else ''

            if plazo < hoy:
                categoria = 'vencido'
                estado = 'VENCIDO'
                voz = f'{saludo()}acuerdo vencido{quien} de la reunión {reunion}: {texto}'
            elif plazo == hoy:
                categoria = 'hoy'
                estado = 'vence HOY'
                voz = f'{saludo()}acuerdo que vence hoy{quien} de la reunión {reunion}: {texto}'
            else:
                categoria = 'manana'
                estado = 'vence mañana'
                voz = f'{saludo()}acuerdo que vence mañana{quien} de la reunión {reunion}: {texto}'

            if categoria == acuerdo.get('ultima_alerta', ''):
                continue

            _avisar(
                f'Acuerdo {estado}',
                f'{texto}\nReunión: {reunion}\nPlazo: {plazo}',
                voz,
            )
            self.db.marcar_alerta_acuerdo_enviada(acuerdo['id'], categoria)
