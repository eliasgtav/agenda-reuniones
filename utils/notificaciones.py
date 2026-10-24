# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
import threading
from datetime import datetime, timedelta
from kivy.utils import platform
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


_tts_android = None
_tts_android_listo = threading.Event()
_tts_android_listener = None  # referencia viva: si jnius lo libera, onInit nunca llega


def _iniciar_tts_android():
    """TextToSpeech nativo de Android, creado UNA vez y reusado. Antes se
    usaba plyer.tts, que crea un TextToSpeech nuevo en cada llamada y habla
    sin esperar a que el motor conecte -- visto con adb logcat (HONOR
    Magic6 Lite, 2026-10-22): "speak failed: not bound to TTS engine" en
    los primeros intentos, y solo sonaba si el motor conectaba dentro de
    los ~10s de reintentos de plyer; si tardaba mas, la alerta se perdia
    sin aviso. plyer ademas fija Locale.US (ingles), que solo no aplicaba
    porque ese setLanguage tambien fallaba por lo mismo. Con targetSdk >= 30
    algunos telefonos tampoco dejan ver el motor de voz sin el <queries>
    TTS_SERVICE del manifest (ver scripts/patch_p4a.py, parche #5)."""
    global _tts_android, _tts_android_listener
    from jnius import autoclass, PythonJavaClass, java_method

    TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
    Locale = autoclass('java.util.Locale')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')

    class _AlIniciar(PythonJavaClass):
        __javainterfaces__ = ['android/speech/tts/TextToSpeech$OnInitListener']
        __javacontext__ = 'app'

        @java_method('(I)V')
        def onInit(self, status):
            if status != TextToSpeech.SUCCESS:
                return
            # Idioma del telefono si ya es espanol (respeta es-MX, es-PE,
            # etc.); si no, espanol generico. < 0 = LANG_MISSING_DATA /
            # LANG_NOT_SUPPORTED.
            local = Locale.getDefault()
            if local.getLanguage() != 'es' or _tts_android.setLanguage(local) < 0:
                _tts_android.setLanguage(Locale('es'))
            _tts_android_listo.set()

    _tts_android_listener = _AlIniciar()
    _tts_android = TextToSpeech(PythonActivity.mActivity, _tts_android_listener)


def _hablar_android(texto):
    if _tts_android is None:
        _iniciar_tts_android()
    if not _tts_android_listo.wait(15):
        return
    from jnius import autoclass
    TextToSpeech = autoclass('android.speech.tts.TextToSpeech')
    String = autoclass('java.lang.String')
    # QUEUE_ADD: varias alertas en el mismo tick se dicen una tras otra en
    # vez de cortarse entre si.
    _tts_android.speak(String(texto), TextToSpeech.QUEUE_ADD, None, String('alerta'))


def _hablar(texto):
    if platform == 'android':
        def _run_android():
            with _engine_voz_lock:
                try:
                    _hablar_android(texto)
                except Exception:
                    import traceback
                    traceback.print_exc()
        threading.Thread(target=_run_android, daemon=True).start()
        return

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


# (lo, hi]: cada alerta suena en el primer tick de 60s en que faltan `hi`
# minutos o menos (o sea entre hi-1 y hi), igual que dice la pantalla.
# Antes la ventana era hi±5, asi que con la app abierta "10 min antes"
# sonaba a los 15. `lo` deja 5 min de gracia si la app se abre tarde, y
# es exclusivo para que dos ventanas contiguas no suenen juntas en el borde.
UMBRALES = {
    '10min': (5, 10),
    '15min': (10, 15),
    '30min': (25, 30),
}

MENSAJES = {
    '10min': 'en 10 minutos',
    '15min': 'en 15 minutos',
    '30min': 'en 30 minutos',
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
            if lo < minutos <= hi:
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
