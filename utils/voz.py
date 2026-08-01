# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
import threading
from kivy.clock import Clock
from kivy.utils import platform


class DictadoVoz:
    """Conecta un botón de micrófono a un campo de texto: dicta con
    SpeechRecognition en escritorio o con la API nativa de Android
    (via plyer.stt) y agrega el texto reconocido al final del campo.
    """

    def __init__(self, campo, boton_mic, lbl_estado=None, on_permiso_denegado=None):
        self.campo = campo
        self.boton_mic = boton_mic
        self.lbl_estado = lbl_estado
        self.on_permiso_denegado = on_permiso_denegado
        self._escuchando = False
        self._color_normal = tuple(boton_mic.icon_color)
        self._ocultar_evento = None

    def toggle(self):
        if self._escuchando:
            return
        self._con_permiso_audio(self._iniciar)

    def _con_permiso_audio(self, on_granted):
        """RECORD_AUDIO en el manifest no basta: Android 6+ exige pedirlo en
        tiempo de ejecucion, si no toda API de audio/voz falla con
        'insufficient_permissions'."""
        if platform != 'android':
            on_granted()
            return
        from android.permissions import check_permission, request_permissions, Permission
        if check_permission(Permission.RECORD_AUDIO):
            on_granted()
            return

        def _en_respuesta(permissions, resultados):
            if resultados and all(resultados):
                Clock.schedule_once(lambda dt: on_granted(), 0)
            elif self.on_permiso_denegado:
                Clock.schedule_once(lambda dt: self.on_permiso_denegado(
                    'Se necesita permiso de micrófono para esta función. '
                    'Actívalo en Ajustes del sistema > Apps > Agenda de Reuniones > Permisos > Micrófono.',
                ), 0)

        request_permissions([Permission.RECORD_AUDIO], _en_respuesta)

    def _iniciar(self):
        self._escuchando = True
        self.boton_mic.icon_color = (0.8, 0.1, 0.1, 1)
        self._estado('🎤 Escuchando... habla ahora')
        if platform == 'android':
            # speech_recognition + PyAudio son librerias de escritorio, no
            # estan en buildozer.spec (PyAudio/portaudio no compila bien
            # para Android). En el telefono se usa la API nativa de Android
            # via plyer.stt.
            self._escuchar_android()
        else:
            threading.Thread(target=self._escuchar_desktop, daemon=True).start()

    def _escuchar_android(self):
        try:
            from plyer import stt
            if not stt.exist():
                self._error('Este dispositivo no tiene reconocimiento de voz disponible.')
                return
            stt._language = 'es-ES'  # el setter publico de plyer solo acepta en-US/pl-PL
            stt.prefer_offline = False
            stt.start()
            Clock.schedule_interval(self._revisar_android, 0.3)
        except Exception as e:
            self._error(f'Error: {e}')

    def _revisar_android(self, dt):
        from plyer import stt
        if stt.listening:
            return
        Clock.unschedule(self._revisar_android)
        if stt.errors:
            err = stt.errors[-1]
            stt.errors = []
            if 'no_match' in err or 'speech_timeout' in err:
                self._error('No se detectó voz. Intenta de nuevo.')
            else:
                self._error(f'Error: {err}')
            return
        if stt.results:
            texto = stt.results[0]
            stt.results = []
            self._insertar(texto)
        else:
            self._error('No se detectó voz.')

    def _escuchar_desktop(self):
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            r.pause_threshold = 1.5
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=10, phrase_time_limit=60)
            texto = r.recognize_google(audio, language='es-ES')
            Clock.schedule_once(lambda dt: self._insertar(texto), 0)
        except Exception as e:
            msg = {
                'WaitTimeoutError': 'Tiempo agotado. No se detectó voz.',
                'UnknownValueError': 'No se entendió. Intenta de nuevo.',
                'RequestError': 'Sin conexión a internet.',
            }.get(type(e).__name__, f'Error: {e}')
            Clock.schedule_once(lambda dt: self._error(msg), 0)

    def _insertar(self, texto):
        campo = self.campo
        actual = campo.text
        sep = ' ' if actual and not actual.endswith('\n') else ''
        # Pasar por insert_text (no reasignar campo.text a mano) para que
        # transformaciones como la mayuscula de CampoOraciones se apliquen
        # tambien al texto dictado, igual que si se hubiera escrito con
        # teclado.
        campo.cursor = campo.get_cursor_from_index(len(actual))
        # El separador se inserta aparte del texto dictado: si van juntos en
        # un solo insert_text, CampoOraciones mayuscula substring[0] (el
        # espacio del separador) en vez de la primera letra real dictada.
        if sep:
            campo.insert_text(sep)
        campo.insert_text(texto)
        self._estado_temporal(f'✓ "{texto[:60]}..."' if len(texto) > 60 else f'✓ "{texto}"')
        self._restaurar()

    def _error(self, msg):
        self._estado_temporal(f'⚠ {msg}')
        self._restaurar()

    def _restaurar(self):
        self.boton_mic.icon_color = self._color_normal
        self._escuchando = False

    def _estado(self, texto):
        if self._ocultar_evento is not None:
            self._ocultar_evento.cancel()
            self._ocultar_evento = None
        if self.lbl_estado:
            self.lbl_estado.text = texto

    def _estado_temporal(self, texto, duracion=3.0):
        """Como _estado, pero la limpia sola tras `duracion` segundos: para
        mensajes finales (exito/error) que no deben quedar pegados en
        pantalla despues de terminar el dictado."""
        self._estado(texto)
        if self.lbl_estado:
            self._ocultar_evento = Clock.schedule_once(self._ocultar_estado, duracion)

    def _ocultar_estado(self, _dt):
        self._ocultar_evento = None
        if self.lbl_estado:
            self.lbl_estado.text = ''
