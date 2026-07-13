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


def _hablar(texto):
    def _run():
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 130)
            voices = engine.getProperty('voices')
            for v in voices:
                if 'ES' in v.id or 'Spanish' in v.name:
                    engine.setProperty('voice', v.id)
                    break
            engine.say(_corregir_pronunciacion(_limpiar_acentos(texto)))
            engine.runAndWait()
        except Exception:
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


UMBRALES = {
    '30min': (25, 35),
    '1hora': (55, 65),
    '1dia':  (1415, 1445),
}

MENSAJES = {
    '30min': 'en 30 minutos',
    '1hora': 'en 1 hora',
    '1dia':  'mañana',
}


class NotificacionesManager:
    def __init__(self, db):
        self.db = db

    def verificar_alertas(self, *args):
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
                partes_nombre = cargar_config().get('nombres', '').split()
                primer_nombre = partes_nombre[0] if partes_nombre else ''
                saludo = f'{primer_nombre}, ' if primer_nombre else ''
                titulo = f'Reunión próxima — {cuando}'
                msg = f'{asunto} ({alerta["hora"]}) — {alerta.get("lugar","")}'
                _notificar(titulo, msg)
                _hablar(
                    f'{saludo}tiene una reunión {cuando}. '
                    f'Asunto: {asunto}.'
                )
                self.db.marcar_alerta_enviada(alerta['id'])
        self.verificar_plazos_acuerdos()

    def verificar_plazos_acuerdos(self):
        from datetime import datetime
        hoy = datetime.now().strftime('%Y-%m-%d')
        partes_nombre = cargar_config().get('nombres', '').split()
        primer_nombre = partes_nombre[0] if partes_nombre else ''
        saludo = f'{primer_nombre}, ' if primer_nombre else ''

        for acuerdo in self.db.acuerdos_con_plazo_pendientes():
            plazo = acuerdo['plazo']
            texto = acuerdo['texto']
            reunion = acuerdo['reunion_asunto']

            if plazo < hoy:
                estado = 'VENCIDO'
                voz = f'{saludo}acuerdo vencido de la reunión {reunion}: {texto}'
            elif plazo == hoy:
                estado = 'vence HOY'
                voz = f'{saludo}acuerdo que vence hoy de la reunión {reunion}: {texto}'
            else:
                estado = 'vence mañana'
                voz = f'{saludo}acuerdo que vence mañana de la reunión {reunion}: {texto}'

            _notificar(
                f'Acuerdo {estado}',
                f'{texto}\nReunión: {reunion}\nPlazo: {plazo}'
            )
            _hablar(voz)
            self.db.marcar_alerta_acuerdo_enviada(acuerdo['id'])
