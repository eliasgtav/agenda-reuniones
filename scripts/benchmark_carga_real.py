# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Carga la base de datos REAL de la app (~/agenda_reuniones.db, la misma
que usa main.py) con reuniones/acuerdos de prueba y mide ahí mismo los
tiempos reales de las consultas que usan las pantallas -- a diferencia de
scripts/benchmark_carga.py (que puebla una base TEMPORAL aparte, nunca toca
tus datos), este script inserta en tu base real para que puedas ver el
efecto directo con tu propio archivo .db, tamaño de disco real, etc.

Todo lo que inserta queda marcado con el prefijo "[PRUEBA] " en el asunto/
texto (mismo criterio que scripts/insertar_datos_prueba.py) -- se puede
borrar después sin tocar ni una reunión real.

Los acuerdos de prueba se generan con plazo SIEMPRE en el futuro (5-180
días) a propósito -- un plazo vencido/hoy/mañana dispara de verdad las
alertas de voz de utils/notificaciones.py cada 60s y satura de avisos al
abrir la app (ya pasó una vez, ver [[project_agenda_seguridad_y_carga]] en
memoria).

Uso:
  py -3.12 scripts/benchmark_carga_real.py            -> inserta 2000 reuniones y mide
  py -3.12 scripts/benchmark_carga_real.py 5000        -> inserta 5000 y mide
  py -3.12 scripts/benchmark_carga_real.py --limpiar   -> borra solo los datos de prueba
                                                           (comparte el borrado con
                                                           insertar_datos_prueba.py --
                                                           mismo prefijo "[PRUEBA] ")

Cierra la app antes de correr esto.
"""
import os
import random
import statistics
import sys
import time

# database.py importa kivy.utils -- eso dispara el parser de argumentos de
# Kivy al importar, que revienta con nuestras propias banderas (--limpiar,
# un numero suelto). Ver mismo fix en insertar_datos_prueba.py.
os.environ.setdefault('KIVY_NO_ARGS', '1')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from scripts.insertar_datos_prueba import (
    PREFIJO, _ASUNTOS, _LUGARES, _ESTADOS, _PESOS_ESTADO, _NOMBRES,
    _PRIORIDADES, _fecha_aleatoria, _plazo_acuerdo_aleatorio, _hora_aleatoria,
    limpiar,
)

REPETICIONES = 15


def poblar(db, n, offset_id):
    """Inserta n reuniones/participantes/acuerdos en bloque (executemany) --
    mucho mas rapido que insertar_datos_prueba.py::insertar() (que abre una
    conexion nueva por cada fila, pensado para volumenes chicos de ~100-500).
    Aqui se prioriza velocidad porque el objetivo es tener volumen para
    medir, no probar el camino de insercion uno-a-uno de la UI."""
    with db._conn() as conn:
        reuniones = []
        for i in range(n):
            asunto = f'{PREFIJO}{random.choice(_ASUNTOS)} #{offset_id + i + 1}'
            reuniones.append((
                asunto, _fecha_aleatoria(), _hora_aleatoria(), random.choice(_LUGARES),
                random.choices(_ESTADOS, weights=_PESOS_ESTADO)[0],
                'presencial' if random.random() > 0.3 else 'virtual',
                '', 'Reunión de prueba generada por scripts/benchmark_carga_real.py', '',
            ))
        conn.executemany(
            '''INSERT INTO reuniones
               (asunto, fecha, hora, lugar, estado, modalidad, desarrollo, notas, conclusion)
               VALUES (?,?,?,?,?,?,?,?,?)''',
            reuniones,
        )
        # NO se puede asumir que el siguiente id sea MAX(id)+1: la columna es
        # AUTOINCREMENT, que nunca reutiliza ids aunque se hayan borrado filas
        # (el contador interno de SQLite sigue avanzando). Con la base REAL,
        # que ya tuvo rondas anteriores de insertar/--limpiar datos de
        # prueba, MAX(id) entre lo que queda puede ser mucho menor que el
        # proximo id real -- calcularlo antes causaba
        # "sqlite3.IntegrityError: FOREIGN KEY constraint failed" porque
        # participantes/acuerdos apuntaban a reunion_id que no existian.
        # last_insert_rowid() sí refleja el ultimo id real insertado por
        # esta conexion, incluso tras un executemany.
        ultimo_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        primer_id = ultimo_id - n + 1
        ids_reunion = list(range(primer_id, primer_id + n))

        participantes = []
        acuerdos = []
        for rid in ids_reunion:
            for _ in range(random.randint(0, 3)):
                participantes.append((rid, random.choice(_NOMBRES), random.choice([0, 1])))
            for _ in range(random.randint(0, 2)):
                plazo = _plazo_acuerdo_aleatorio() if random.random() > 0.3 else ''
                acuerdos.append((
                    rid, f'{PREFIJO}Acuerdo de seguimiento #{rid}',
                    plazo, _hora_aleatoria() if plazo else '',
                    random.choice(_NOMBRES),
                    random.choices(['pendiente', 'completado'], weights=[0.6, 0.4])[0],
                    random.choice(_PRIORIDADES),
                ))

        if participantes:
            conn.executemany(
                'INSERT INTO participantes (reunion_id, nombre, asistio) VALUES (?,?,?)',
                participantes,
            )
        if acuerdos:
            conn.executemany(
                '''INSERT INTO acuerdos
                   (reunion_id, texto, plazo, plazo_hora, responsable, estado, prioridad)
                   VALUES (?,?,?,?,?,?,?)''',
                acuerdos,
            )
    return ids_reunion


def medir(fn, reps=REPETICIONES):
    tiempos = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        tiempos.append((time.perf_counter() - t0) * 1000)
    return tiempos


def reportar(nombre, tiempos):
    print(f'  {nombre:<42} avg={statistics.mean(tiempos):8.2f}ms  '
          f'min={min(tiempos):8.2f}ms  max={max(tiempos):8.2f}ms')


def main(n):
    db = Database()
    print(f'Base de datos REAL: {db.db_path}')
    with db._conn() as conn:
        antes = conn.execute('SELECT COUNT(*) FROM reuniones').fetchone()[0]
    print(f'Reuniones ya existentes antes de insertar: {antes}')

    t0 = time.perf_counter()
    poblar(db, n, offset_id=antes)
    t_insert = time.perf_counter() - t0

    with db._conn() as conn:
        despues = conn.execute('SELECT COUNT(*) FROM reuniones').fetchone()[0]
    tam_mb = os.path.getsize(db.db_path) / (1024 * 1024)
    print(f'Insertadas {n} reuniones de prueba en {t_insert:.2f}s '
          f'(total ahora: {despues}, .db pesa {tam_mb:.1f} MB)\n')

    print('=== Tiempos de consulta con el volumen actual de tu base real ===')
    reportar('listar_reuniones() sin filtro (todo)', medir(lambda: db.listar_reuniones()))
    reportar('listar_reuniones(limit=40) -- 1a pagina real', medir(lambda: db.listar_reuniones(limit=40, offset=0)))
    reportar('listar_reuniones(estado=pendiente, limit=40)', medir(lambda: db.listar_reuniones(estado='pendiente', limit=40, offset=0)))
    reportar('listar_reuniones(estado=hoy)', medir(lambda: db.listar_reuniones(estado='hoy')))
    reportar('listar_reuniones(busqueda=texto, limit=40)', medir(lambda: db.listar_reuniones(busqueda='seguimiento', limit=40, offset=0)))
    reportar('stats_dashboard()', medir(lambda: db.stats_dashboard()))
    reportar('reuniones_hoy()', medir(lambda: db.reuniones_hoy()))
    reportar('listar_todos_acuerdos() sin filtro (todo)', medir(lambda: db.listar_todos_acuerdos()))
    reportar('listar_todos_acuerdos(limit=40) -- 1a pagina real', medir(lambda: db.listar_todos_acuerdos(limit=40, offset=0)))
    reportar('listar_todos_acuerdos(estado=vencido)', medir(lambda: db.listar_todos_acuerdos(estado='vencido')))
    reportar('contar_acuerdos_activos()', medir(lambda: db.contar_acuerdos_activos()))
    reportar('acuerdos_con_plazo_pendientes()', medir(lambda: db.acuerdos_con_plazo_pendientes()))
    reportar('obtener_reunion(id) puntual', medir(lambda: db.obtener_reunion(random.randint(1, despues))))

    print('\nPara quitar los datos de prueba: py -3.12 scripts/benchmark_carga_real.py --limpiar')
    print('(el borrado es compartido con scripts/insertar_datos_prueba.py -- mismo prefijo)')


if __name__ == '__main__':
    if '--limpiar' in sys.argv:
        limpiar()
    else:
        n = 2000
        for arg in sys.argv[1:]:
            if arg.isdigit():
                n = int(arg)
        main(n)
