# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Inserta reuniones/acuerdos de PRUEBA en la base de datos REAL de la app
(la misma que usa main.py, normalmente ~/agenda_reuniones.db) -- para poder
ver el scroll infinito / paginación de Lista de Reuniones y Seguimiento de
Acuerdos funcionando de verdad en la pantalla, en vez de con las pocas
reuniones reales que ya tengas cargadas.

Todo lo que este script inserta queda marcado con el prefijo "[PRUEBA] " en
el asunto (reuniones) o en el texto (acuerdos) -- así se puede identificar y
borrar después sin tocar ni una sola reunión real.

Uso (desde la carpeta del proyecto):
  py -3.12 scripts/insertar_datos_prueba.py            -> inserta 150 reuniones de prueba
  py -3.12 scripts/insertar_datos_prueba.py 500         -> inserta 500 reuniones de prueba
  py -3.12 scripts/insertar_datos_prueba.py --limpiar   -> BORRA solo las reuniones de
                                                            prueba (las que empiezan con
                                                            "[PRUEBA] "); el resto de tus
                                                            datos reales no se toca.

Cierra la app antes de correr esto para evitar que dos procesos escriban en
la base de datos al mismo tiempo (SQLite lo tolera, pero es más limpio).
Después de insertar, reabre la app y entra a "Lista de reuniones" o
"Seguimiento de acuerdos" para ver las tarjetas nuevas y probar el scroll.
"""
import os
import random
import sys
from datetime import datetime, timedelta

# database.py importa kivy.utils -- eso dispara el parser de linea de
# comandos propio de Kivy al importar, que revienta con "option --limpiar
# not recognized" (exit code 2) porque no reconoce nuestras propias
# banderas. KIVY_NO_ARGS=1 lo desactiva -- este script no es una app grafica,
# no necesita ninguna opcion de Kivy.
os.environ.setdefault('KIVY_NO_ARGS', '1')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database

PREFIJO = '[PRUEBA] '

_ASUNTOS = [
    'Revisión de presupuesto', 'Planeación trimestral', 'Seguimiento de proyecto',
    'Cierre de mes', 'Comité de calidad', 'Revisión de indicadores',
    'Kickoff de proyecto', 'Retroalimentación de equipo', 'Auditoría interna',
    'Negociación con proveedor', 'Capacitación de personal', 'Revisión legal',
    'Planeación de ventas', 'Reunión de dirección',
]
_LUGARES = ['Sala A', 'Sala B', 'Oficina 301', 'Virtual - Zoom', 'Virtual - Meet', 'Sala de juntas']
_ESTADOS = ['pendiente', 'realizada', 'cancelada', 'no_asistida']
_PESOS_ESTADO = [0.35, 0.45, 0.10, 0.10]
_NOMBRES = [
    'Ana López', 'Carlos Ruiz', 'María Fernández', 'Jorge Torres',
    'Lucía Ramírez', 'Pedro Sánchez', 'Sofía Herrera', 'Diego Morales',
]
_PRIORIDADES = ['baja', 'media', 'alta']


def _fecha_aleatoria():
    dias = random.randint(-180, 90)
    return (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d')


def _plazo_acuerdo_aleatorio():
    # SIEMPRE futuro con margen (nunca hoy/manana/vencido) -- a diferencia de
    # _fecha_aleatoria() de arriba. Un plazo pasado o cercano dispara de
    # verdad utils/notificaciones.py::verificar_plazos_acuerdos (corre cada
    # 60s desde main.py::_check_alertas) y satura de avisos de voz apenas se
    # abre la app -- ya paso una vez en la sesion 2026-08-22 (ver
    # [[project_agenda_seguridad_y_carga]]).
    dias = random.randint(5, 180)
    return (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d')


def _hora_aleatoria():
    return f'{random.randint(7, 19):02d}:{random.choice(["00", "15", "30", "45"])}'


def insertar(n):
    db = Database()
    print(f'Insertando {n} reuniones de prueba en: {db.db_path}')
    for i in range(n):
        asunto = f'{PREFIJO}{random.choice(_ASUNTOS)} #{i + 1}'
        rid = db.crear_reunion(
            asunto, _fecha_aleatoria(), _hora_aleatoria(),
            lugar=random.choice(_LUGARES),
            notas='Reunión de prueba generada por scripts/insertar_datos_prueba.py',
        )
        db.actualizar_reunion(rid, estado=random.choices(_ESTADOS, weights=_PESOS_ESTADO)[0])
        for _ in range(random.randint(0, 3)):
            db.agregar_participante(rid, random.choice(_NOMBRES), random.choice([0, 1]))
        for _ in range(random.randint(0, 2)):
            plazo = _plazo_acuerdo_aleatorio() if random.random() > 0.3 else ''
            db.guardar_acuerdo(
                rid, f'{PREFIJO}Acuerdo de seguimiento #{i + 1}',
                plazo=plazo,
                plazo_hora=_hora_aleatoria() if plazo else '',
                responsable=random.choice(_NOMBRES),
                prioridad=random.choice(_PRIORIDADES),
            )
        if (i + 1) % 50 == 0:
            print(f'  ...{i + 1}/{n}')
    print(f'Listo: {n} reuniones de prueba insertadas (con participantes y acuerdos de muestra).')
    print('Para quitarlas después: py -3.12 scripts/insertar_datos_prueba.py --limpiar')


def limpiar():
    db = Database()
    with db._conn() as conn:
        ids = [r[0] for r in conn.execute(
            'SELECT id FROM reuniones WHERE asunto LIKE ?', (f'{PREFIJO}%',)
        ).fetchall()]
        # ON DELETE CASCADE (activado con PRAGMA foreign_keys=ON en cada
        # conexión, ver database.py::_conn) borra solo tambien
        # participantes/archivos/alertas/acuerdos de esas reuniones.
        conn.execute('DELETE FROM reuniones WHERE asunto LIKE ?', (f'{PREFIJO}%',))
    print(f'Borradas {len(ids)} reuniones de prueba (y sus participantes/acuerdos '
          'relacionados). El resto de tus reuniones reales no se tocó.')


if __name__ == '__main__':
    if '--limpiar' in sys.argv:
        limpiar()
    else:
        n = 150
        for arg in sys.argv[1:]:
            if arg.isdigit():
                n = int(arg)
        insertar(n)
