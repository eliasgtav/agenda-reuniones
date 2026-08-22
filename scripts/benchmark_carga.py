# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Prueba de carga local de database.py.

La app no tiene servidor ni usuarios concurrentes (cada instalación corre
sola, SQLite local) -- lo que sí es medible es cómo se comportan las
consultas reales que usan las pantallas (Dashboard, Lista de Reuniones,
Seguimiento de Acuerdos) a medida que crece el VOLUMEN de datos guardados
en un mismo dispositivo con el tiempo.

Este script:
  1. Crea una base de datos SQLite temporal aparte (NUNCA toca
     agenda_reuniones.db real del usuario).
  2. La puebla con miles de reuniones/participantes/acuerdos sintéticos,
     insertados en bloque (executemany) -- rápido, solo para tener volumen
     que consultar. Esto es distinto a cómo el usuario realmente carga
     datos (una reunión a la vez desde la UI); no mide velocidad de
     inserción real, mide tiempos de CONSULTA con distintos volúmenes.
  3. En varios puntos de escala (100 a 10000 reuniones), llama a los
     mismos métodos de Database que usan las pantallas reales y mide
     cuánto tardan.

Uso: py -3.12 scripts/benchmark_carga.py
"""
import os
import random
import statistics
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as database_module

_DB_TEMPORAL = os.path.join(tempfile.gettempdir(), 'agenda_benchmark.db')


def _ruta_temporal():
    return _DB_TEMPORAL


# Se reemplaza ANTES de importar/instanciar Database para que _get_db_path()
# nunca apunte a la base de datos real del usuario en ~/agenda_reuniones.db.
database_module._get_db_path = _ruta_temporal

from database import Database  # noqa: E402  (import tardío a propósito)


ESCALAS = [100, 500, 1000, 2500, 5000, 10000]
REPETICIONES = 15  # veces que se corre cada consulta para sacar avg/min/max

_ASUNTOS = [
    'Revisión de presupuesto', 'Planeación trimestral', 'Seguimiento de proyecto',
    'Cierre de mes', 'Comité de calidad', 'Revisión de indicadores',
    'Kickoff de proyecto', 'Retroalimentación de equipo', 'Auditoría interna',
    'Negociación con proveedor', 'Capacitación de personal', 'Revisión legal',
    'Planeación de ventas', 'Seguimiento de acuerdos', 'Reunión de dirección',
]
_LUGARES = ['Sala A', 'Sala B', 'Oficina 301', 'Virtual - Zoom', 'Virtual - Meet', 'Sala de juntas']
_ESTADOS_REUNION = ['pendiente', 'realizada', 'cancelada', 'no_asistida']
_PESOS_ESTADO = [0.35, 0.45, 0.10, 0.10]
_NOMBRES = [
    'Ana López', 'Carlos Ruiz', 'Elías Gaytan', 'María Fernández', 'Jorge Torres',
    'Lucía Ramírez', 'Pedro Sánchez', 'Sofía Herrera', 'Diego Morales', 'Valeria Cruz',
]
_PRIORIDADES = ['baja', 'media', 'alta']
_ESTADOS_ACUERDO = ['pendiente', 'completado']

_RELLENO = (
    'Se discutieron los puntos principales de la agenda, incluyendo avances, '
    'riesgos identificados y próximos pasos a seguir por cada responsable. '
) * 3  # ~250 caracteres, simula notas/conclusión con contenido real


def _fecha_aleatoria():
    dias = random.randint(-365, 180)
    from datetime import datetime, timedelta
    return (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d')


def _hora_aleatoria():
    return f'{random.randint(7, 19):02d}:{random.choice(["00", "15", "30", "45"])}'


def poblar(db, n_reuniones, offset_id=0):
    """Inserta n_reuniones (+ participantes/acuerdos/archivos/alertas
    relacionados) en bloque. Devuelve los ids de reuniones insertadas."""
    with db._conn() as conn:
        primer_id = (conn.execute('SELECT COALESCE(MAX(id), 0) FROM reuniones').fetchone()[0]) + 1
        reuniones = []
        for i in range(n_reuniones):
            asunto = f'{random.choice(_ASUNTOS)} #{offset_id + i}'
            reuniones.append((
                asunto,
                _fecha_aleatoria(),
                _hora_aleatoria(),
                random.choice(_LUGARES),
                random.choices(_ESTADOS_REUNION, weights=_PESOS_ESTADO)[0],
                'presencial' if random.random() > 0.3 else 'virtual',
                _RELLENO,
                _RELLENO,
                _RELLENO if random.random() > 0.4 else '',
            ))
        # cursor.lastrowid queda en None tras executemany() (no lo garantiza
        # la API de sqlite3) -- se calculan los ids a partir del MAX(id)
        # anterior, válido porque este script tiene la base de datos
        # temporal para sí solo (sin borrados intercalados que dejen huecos).
        conn.executemany(
            '''INSERT INTO reuniones
               (asunto, fecha, hora, lugar, estado, modalidad, desarrollo, notas, conclusion)
               VALUES (?,?,?,?,?,?,?,?,?)''',
            reuniones,
        )
        ids_reunion = list(range(primer_id, primer_id + n_reuniones))

        participantes = []
        acuerdos = []
        archivos = []
        alertas = []
        for rid in ids_reunion:
            for _ in range(random.randint(0, 4)):
                participantes.append((rid, random.choice(_NOMBRES), random.choice([0, 1])))
            for _ in range(random.randint(0, 3)):
                plazo = _fecha_aleatoria() if random.random() > 0.3 else ''
                acuerdos.append((
                    rid,
                    f'Acuerdo de seguimiento para {random.choice(_ASUNTOS)}',
                    plazo,
                    _hora_aleatoria() if plazo else '',
                    random.choice(_NOMBRES),
                    random.choices(_ESTADOS_ACUERDO, weights=[0.6, 0.4])[0],
                    random.choice(_PRIORIDADES),
                ))
            for _ in range(random.randint(0, 1)):
                archivos.append((rid, 'documento.pdf', f'/adjuntos/{rid}_doc.pdf', 'documento'))
            for tipo in random.sample(['30min', '1h', '1dia'], k=random.randint(0, 2)):
                alertas.append((rid, tipo))

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
        if archivos:
            conn.executemany(
                'INSERT INTO archivos (reunion_id, nombre, ruta, tipo) VALUES (?,?,?,?)',
                archivos,
            )
        if alertas:
            conn.executemany(
                'INSERT INTO alertas (reunion_id, tipo) VALUES (?,?)',
                alertas,
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
    return statistics.mean(tiempos)


def main():
    if os.path.exists(_DB_TEMPORAL):
        os.remove(_DB_TEMPORAL)

    random.seed(42)  # reproducible entre corridas
    db = Database()

    acumulado = 0
    resultados_por_escala = {}
    t_total_insercion = 0.0

    for escala in ESCALAS:
        faltan = escala - acumulado
        t0 = time.perf_counter()
        poblar(db, faltan, offset_id=acumulado)
        t_insert = time.perf_counter() - t0
        t_total_insercion += t_insert
        acumulado = escala

        tam_mb = os.path.getsize(_DB_TEMPORAL) / (1024 * 1024)
        print(f'\n=== {escala:>6} reuniones  '
              f'(+{faltan} insertadas en {t_insert:.2f}s, .db pesa {tam_mb:.1f} MB) ===')

        peores = {}
        peores['listar_reuniones() sin filtro'] = reportar(
            'listar_reuniones() sin filtro', medir(lambda: db.listar_reuniones()))
        peores['listar_reuniones(estado=pendiente)'] = reportar(
            'listar_reuniones(estado=pendiente)', medir(lambda: db.listar_reuniones(estado='pendiente')))
        peores['listar_reuniones(estado=hoy)'] = reportar(
            'listar_reuniones(estado=hoy)', medir(lambda: db.listar_reuniones(estado='hoy')))
        peores['listar_reuniones(busqueda=texto)'] = reportar(
            'listar_reuniones(busqueda="seguimiento")', medir(lambda: db.listar_reuniones(busqueda='seguimiento')))
        peores['stats_dashboard()'] = reportar(
            'stats_dashboard()', medir(lambda: db.stats_dashboard()))
        peores['reuniones_hoy()'] = reportar(
            'reuniones_hoy()', medir(lambda: db.reuniones_hoy()))
        peores['listar_todos_acuerdos() sin filtro'] = reportar(
            'listar_todos_acuerdos() sin filtro', medir(lambda: db.listar_todos_acuerdos()))
        peores['listar_todos_acuerdos(estado=vencido)'] = reportar(
            'listar_todos_acuerdos(estado=vencido)', medir(lambda: db.listar_todos_acuerdos(estado='vencido')))
        peores['listar_todos_acuerdos(busqueda=texto)'] = reportar(
            'listar_todos_acuerdos(busqueda="seguimiento")',
            medir(lambda: db.listar_todos_acuerdos(busqueda='seguimiento')))
        peores['contar_acuerdos_activos()'] = reportar(
            'contar_acuerdos_activos()', medir(lambda: db.contar_acuerdos_activos()))
        peores['acuerdos_con_plazo_pendientes()'] = reportar(
            'acuerdos_con_plazo_pendientes()', medir(lambda: db.acuerdos_con_plazo_pendientes()))
        peores['obtener_reunion(id) puntual'] = reportar(
            'obtener_reunion(id) puntual', medir(lambda: db.obtener_reunion(random.choice(range(1, acumulado + 1)))))

        resultados_por_escala[escala] = peores

    print(f'\n\nTiempo total de inserción sintética (bloque, no representa uso real): '
          f'{t_total_insercion:.2f}s para {acumulado} reuniones')
    print(f'Tamaño final de la base de datos: {os.path.getsize(_DB_TEMPORAL)/(1024*1024):.1f} MB')

    print('\n=== RESUMEN: crecimiento del tiempo con el volumen (avg ms) ===')
    consultas = list(next(iter(resultados_por_escala.values())).keys())
    ancho = max(len(c) for c in consultas)
    header = f'{"consulta":<{ancho}}  ' + '  '.join(f'{e:>8}' for e in ESCALAS)
    print(header)
    for c in consultas:
        fila = f'{c:<{ancho}}  ' + '  '.join(f'{resultados_por_escala[e][c]:8.2f}' for e in ESCALAS)
        print(fila)

    peor_10k = max(resultados_por_escala[ESCALAS[-1]].items(), key=lambda kv: kv[1])
    print(f'\nConsulta más lenta en {ESCALAS[-1]} reuniones: '
          f'"{peor_10k[0]}" -> {peor_10k[1]:.2f}ms de promedio')
    print('\nRecordatorio: database.py no tiene ningún índice creado aparte de las '
          'llaves primarias -- las consultas con WHERE estado=?, fecha=? o LIKE ?%? '
          'hacen un recorrido completo de la tabla (full table scan). Si el tiempo '
          'crece de forma notoria con el volumen en la tabla de arriba, la mejora '
          'de fondo sería agregar índices en reuniones(fecha), reuniones(estado) y '
          'acuerdos(reunion_id) -- no aplicado en este script, solo medido.')

    try:
        os.remove(_DB_TEMPORAL)
    except PermissionError:
        # database.py::Database._conn() abre una conexión sqlite3 nueva por
        # llamada y solo hace commit al salir del "with" -- nunca la cierra
        # explícitamente (patrón usado en todo el proyecto, no exclusivo de
        # este script). En Windows eso puede dejar el archivo bloqueado un
        # momento tras la última consulta. No es crítico aquí: es un archivo
        # temporal, se limpia solo la próxima vez que se corra el script
        # (se borra al inicio) o cuando Windows limpie %TEMP%.
        print(f'\n(No se pudo borrar {_DB_TEMPORAL} de inmediato -- Windows aún '
              'tiene el archivo abierto. No afecta los resultados; se sobreescribe '
              'solo en la próxima corrida.)')


if __name__ == '__main__':
    main()
