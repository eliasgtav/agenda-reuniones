# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
import sqlite3
import os
from datetime import datetime, timedelta
from kivy.utils import platform


def _get_db_path():
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
                base = os.path.expanduser('~')
    else:
        base = os.path.expanduser('~')
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        base = os.path.expanduser('~')
    return os.path.join(base, 'agenda_reuniones.db')


class Database:
    def __init__(self):
        self.db_path = _get_db_path()
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS reuniones (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    asunto        TEXT    NOT NULL,
                    fecha         TEXT    NOT NULL,
                    hora          TEXT    NOT NULL DEFAULT '09:00',
                    lugar         TEXT    DEFAULT '',
                    estado        TEXT    DEFAULT 'pendiente',
                    modalidad     TEXT    DEFAULT 'presencial',
                    desarrollo    TEXT    DEFAULT '',
                    notas         TEXT    DEFAULT '',
                    conclusion    TEXT    DEFAULT '',
                    grabacion_path TEXT   DEFAULT '',
                    created_at    TEXT    DEFAULT (datetime('now','localtime')),
                    updated_at    TEXT    DEFAULT (datetime('now','localtime'))
                );

                CREATE TABLE IF NOT EXISTS participantes (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    reunion_id INTEGER NOT NULL,
                    nombre     TEXT    NOT NULL,
                    asistio    INTEGER DEFAULT 1,
                    FOREIGN KEY (reunion_id) REFERENCES reuniones(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS archivos (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    reunion_id INTEGER NOT NULL,
                    nombre     TEXT    NOT NULL,
                    ruta       TEXT    NOT NULL,
                    tipo       TEXT    DEFAULT 'documento',
                    created_at TEXT    DEFAULT (datetime('now','localtime')),
                    FOREIGN KEY (reunion_id) REFERENCES reuniones(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS alertas (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    reunion_id INTEGER NOT NULL,
                    tipo       TEXT    NOT NULL,
                    enviada    INTEGER DEFAULT 0,
                    FOREIGN KEY (reunion_id) REFERENCES reuniones(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS acuerdos (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    reunion_id  INTEGER NOT NULL,
                    texto       TEXT    NOT NULL,
                    plazo       TEXT    DEFAULT '',
                    plazo_hora  TEXT    DEFAULT '',
                    responsable TEXT    DEFAULT '',
                    estado      TEXT    DEFAULT 'pendiente',
                    prioridad   TEXT    DEFAULT 'media',
                    alerta_enviada INTEGER DEFAULT 0,
                    ultima_alerta  TEXT    DEFAULT '',
                    created_at  TEXT    DEFAULT (datetime('now','localtime')),
                    FOREIGN KEY (reunion_id) REFERENCES reuniones(id) ON DELETE CASCADE
                );

                -- Sin estos indices, listar_reuniones/listar_todos_acuerdos/
                -- stats_dashboard hacian un recorrido completo de la tabla en
                -- cada WHERE estado=?/fecha=?/reunion_id=?/plazo<=? -- medido
                -- con scripts/benchmark_carga.py: ~290ms para listar 10000
                -- reuniones sin filtro, creciendo peor que lineal con el
                -- volumen. CREATE INDEX IF NOT EXISTS es idempotente y se
                -- aplica solo en instalaciones existentes (no requiere
                -- migracion ALTER TABLE como las columnas de mas abajo).
                CREATE INDEX IF NOT EXISTS idx_reuniones_fecha ON reuniones(fecha);
                CREATE INDEX IF NOT EXISTS idx_reuniones_estado ON reuniones(estado);
                CREATE INDEX IF NOT EXISTS idx_participantes_reunion ON participantes(reunion_id);
                CREATE INDEX IF NOT EXISTS idx_archivos_reunion ON archivos(reunion_id);
                CREATE INDEX IF NOT EXISTS idx_alertas_reunion ON alertas(reunion_id);
                CREATE INDEX IF NOT EXISTS idx_acuerdos_reunion ON acuerdos(reunion_id);
                CREATE INDEX IF NOT EXISTS idx_acuerdos_estado ON acuerdos(estado);
                CREATE INDEX IF NOT EXISTS idx_acuerdos_plazo ON acuerdos(plazo);
            ''')
            # Instalaciones existentes ya tenian la tabla 'reuniones' sin
            # columnas agregadas despues; CREATE TABLE IF NOT EXISTS no las
            # agrega sola, hace falta ALTER TABLE. Ignorar el error si la
            # columna ya existe (instalacion nueva o ya migrada).
            for ddl in (
                "ALTER TABLE reuniones ADD COLUMN modalidad TEXT DEFAULT 'presencial'",
                "ALTER TABLE reuniones ADD COLUMN desarrollo TEXT DEFAULT ''",
                "ALTER TABLE acuerdos ADD COLUMN responsable TEXT DEFAULT ''",
                "ALTER TABLE acuerdos ADD COLUMN estado TEXT DEFAULT 'pendiente'",
                "ALTER TABLE acuerdos ADD COLUMN prioridad TEXT DEFAULT 'media'",
                "ALTER TABLE acuerdos ADD COLUMN plazo_hora TEXT DEFAULT ''",
                "ALTER TABLE acuerdos ADD COLUMN ultima_alerta TEXT DEFAULT ''",
            ):
                try:
                    conn.execute(ddl)
                except sqlite3.OperationalError:
                    pass

    # ── Reuniones ──────────────────────────────────────────────────────────────

    def crear_reunion(self, asunto, fecha, hora, lugar='', notas='', tipos_alerta=None, modalidad='presencial'):
        with self._conn() as conn:
            cur = conn.execute(
                'INSERT INTO reuniones (asunto, fecha, hora, lugar, notas, modalidad) VALUES (?,?,?,?,?,?)',
                (asunto, fecha, hora, lugar, notas, modalidad),
            )
            rid = cur.lastrowid
            if tipos_alerta:
                for t in tipos_alerta:
                    conn.execute(
                        'INSERT INTO alertas (reunion_id, tipo) VALUES (?,?)', (rid, t)
                    )
            return rid

    def actualizar_reunion(self, reunion_id, **kwargs):
        kwargs['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sets = ', '.join(f'{k}=?' for k in kwargs)
        vals = list(kwargs.values()) + [reunion_id]
        with self._conn() as conn:
            conn.execute(f'UPDATE reuniones SET {sets} WHERE id=?', vals)

    def obtener_reunion(self, reunion_id):
        with self._conn() as conn:
            row = conn.execute('SELECT * FROM reuniones WHERE id=?', (reunion_id,)).fetchone()
            return dict(row) if row else None

    def listar_reuniones(self, estado=None, busqueda=None, limit=None, offset=0):
        query = 'SELECT * FROM reuniones'
        params = []
        conds = []
        if estado == 'hoy':
            conds.append('fecha=?')
            params.append(datetime.now().strftime('%Y-%m-%d'))
        elif estado and estado != 'todas':
            conds.append('estado=?')
            params.append(estado)
        if busqueda:
            conds.append('(asunto LIKE ? OR lugar LIKE ?)')
            params += [f'%{busqueda}%', f'%{busqueda}%']
        if conds:
            query += ' WHERE ' + ' AND '.join(conds)
        query += ' ORDER BY fecha DESC, hora DESC'
        # limit=None (por defecto) mantiene el comportamiento de siempre --
        # trae todo, usado por Exportar a Excel y cualquier otro llamador que
        # necesite el conjunto completo, no solo una pagina.
        if limit is not None:
            query += ' LIMIT ? OFFSET ?'
            params += [limit, offset]
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    @staticmethod
    def _borrar_archivos_fisicos(rutas):
        # Best-effort: un archivo ya movido/borrado a mano por el usuario no
        # debe impedir que el borrado en la BD (la parte que importa) siga
        # adelante.
        for ruta in rutas:
            if not ruta:
                continue
            try:
                os.remove(ruta)
            except OSError:
                pass

    def eliminar_reunion(self, reunion_id):
        with self._conn() as conn:
            rutas = [r['ruta'] for r in conn.execute(
                'SELECT ruta FROM archivos WHERE reunion_id=?', (reunion_id,)
            ).fetchall()]
            grabacion = conn.execute(
                'SELECT grabacion_path FROM reuniones WHERE id=?', (reunion_id,)
            ).fetchone()
            if grabacion and grabacion['grabacion_path']:
                rutas.append(grabacion['grabacion_path'])
            conn.execute('DELETE FROM reuniones WHERE id=?', (reunion_id,))
        self._borrar_archivos_fisicos(rutas)

    def eliminar_todas_reuniones(self):
        # Antes screens/perfil_screen.py corria 'DELETE FROM reuniones' a
        # mano contra app.db._conn() en vez de pasar por Database -- ademas
        # de saltarse la clase que se supone es el unico punto de acceso a
        # la BD, eso dejaba huerfanos en disco todos los adjuntos y
        # grabaciones (ON DELETE CASCADE limpia las filas de 'archivos' pero
        # nunca toco el archivo fisico que esa fila apuntaba).
        with self._conn() as conn:
            rutas = [r['ruta'] for r in conn.execute('SELECT ruta FROM archivos').fetchall()]
            rutas += [
                r['grabacion_path'] for r in conn.execute(
                    "SELECT grabacion_path FROM reuniones WHERE grabacion_path != ''"
                ).fetchall()
            ]
            conn.execute('DELETE FROM reuniones')
        self._borrar_archivos_fisicos(rutas)

    def stats_dashboard(self):
        hoy = datetime.now().strftime('%Y-%m-%d')
        with self._conn() as conn:
            def count(sql, *args):
                return conn.execute(sql, args).fetchone()[0]
            return {
                'total':       count('SELECT COUNT(*) FROM reuniones'),
                'hoy':         count('SELECT COUNT(*) FROM reuniones WHERE fecha=?', hoy),
                'pendientes':  count("SELECT COUNT(*) FROM reuniones WHERE estado='pendiente'"),
                'realizadas':  count("SELECT COUNT(*) FROM reuniones WHERE estado='realizada'"),
                'canceladas':  count("SELECT COUNT(*) FROM reuniones WHERE estado='cancelada'"),
                'no_asistidas':count("SELECT COUNT(*) FROM reuniones WHERE estado='no_asistida'"),
            }

    def reuniones_hoy(self):
        hoy = datetime.now().strftime('%Y-%m-%d')
        with self._conn() as conn:
            rows = conn.execute(
                'SELECT * FROM reuniones WHERE fecha=? ORDER BY hora', (hoy,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Participantes ──────────────────────────────────────────────────────────

    def agregar_participante(self, reunion_id, nombre, asistio=1):
        with self._conn() as conn:
            conn.execute(
                'INSERT INTO participantes (reunion_id, nombre, asistio) VALUES (?,?,?)',
                (reunion_id, nombre, asistio),
            )

    def listar_participantes(self, reunion_id):
        with self._conn() as conn:
            rows = conn.execute(
                'SELECT * FROM participantes WHERE reunion_id=? ORDER BY nombre',
                (reunion_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def listar_participantes_agrupados(self, reunion_ids):
        """Como listar_participantes() pero para varias reuniones a la vez,
        agrupados en un dict {reunion_id: [participantes]} -- usado por
        utils/exportar.py para no hacer una consulta por fila al exportar N
        reuniones (antes N consultas 'WHERE reunion_id=?' separadas)."""
        reunion_ids = list(reunion_ids)
        if not reunion_ids:
            return {}
        with self._conn() as conn:
            placeholders = ','.join('?' * len(reunion_ids))
            rows = conn.execute(
                f'SELECT * FROM participantes WHERE reunion_id IN ({placeholders}) ORDER BY nombre',
                reunion_ids,
            ).fetchall()
        agrupado = {rid: [] for rid in reunion_ids}
        for row in rows:
            agrupado[row['reunion_id']].append(dict(row))
        return agrupado

    def actualizar_asistencia(self, participante_id, asistio):
        with self._conn() as conn:
            conn.execute(
                'UPDATE participantes SET asistio=? WHERE id=?', (asistio, participante_id)
            )

    def eliminar_participante(self, participante_id):
        with self._conn() as conn:
            conn.execute('DELETE FROM participantes WHERE id=?', (participante_id,))

    # ── Archivos ───────────────────────────────────────────────────────────────

    def agregar_archivo(self, reunion_id, nombre, ruta, tipo='documento'):
        with self._conn() as conn:
            conn.execute(
                'INSERT INTO archivos (reunion_id, nombre, ruta, tipo) VALUES (?,?,?,?)',
                (reunion_id, nombre, ruta, tipo),
            )

    def listar_archivos(self, reunion_id):
        with self._conn() as conn:
            rows = conn.execute(
                'SELECT * FROM archivos WHERE reunion_id=?', (reunion_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def eliminar_archivo(self, archivo_id):
        with self._conn() as conn:
            fila = conn.execute(
                'SELECT ruta FROM archivos WHERE id=?', (archivo_id,)
            ).fetchone()
            conn.execute('DELETE FROM archivos WHERE id=?', (archivo_id,))
        if fila:
            self._borrar_archivos_fisicos([fila['ruta']])

    # ── Alertas ────────────────────────────────────────────────────────────────

    def auto_cancelar_vencidas(self):
        # Solo cancela reuniones que lleven más de 1 hora sin iniciarse.
        # `(fecha || ' ' || hora) < ?` (como estaba antes) impide usar
        # idx_reuniones_fecha/idx_reuniones_estado -- ningun indice cubre el
        # resultado de concatenar dos columnas en tiempo de consulta, asi que
        # esto corria como recorrido completo cada 60s
        # (main.py::_check_alertas). Separar fecha/hora en la condicion deja
        # ambas columnas comparables tal cual, sargable para los indices.
        limite_dt = datetime.now() - timedelta(hours=1)
        limite_fecha = limite_dt.strftime('%Y-%m-%d')
        limite_hora = limite_dt.strftime('%H:%M')
        cond = '''estado = 'pendiente'
                  AND (fecha < ? OR (fecha = ? AND hora < ?))'''
        params = (limite_fecha, limite_fecha, limite_hora)
        with self._conn() as conn:
            vencidas = conn.execute(
                f'SELECT asunto FROM reuniones WHERE {cond}', params
            ).fetchall()
            if vencidas:
                conn.execute(
                    f"UPDATE reuniones SET estado = 'cancelada', "
                    f"updated_at = datetime('now','localtime') WHERE {cond}",
                    params,
                )
            return [r['asunto'] for r in vencidas]

    def alertas_pendientes(self):
        with self._conn() as conn:
            rows = conn.execute('''
                SELECT a.id, a.tipo, a.enviada,
                       r.asunto, r.fecha, r.hora, r.lugar
                FROM alertas a
                JOIN reuniones r ON r.id = a.reunion_id
                WHERE a.enviada=0 AND r.estado='pendiente'
            ''').fetchall()
            return [dict(r) for r in rows]

    def marcar_alerta_enviada(self, alerta_id):
        with self._conn() as conn:
            conn.execute('UPDATE alertas SET enviada=1 WHERE id=?', (alerta_id,))

    # ── Acuerdos ───────────────────────────────────────────────────────────────

    def guardar_acuerdo(self, reunion_id, texto, plazo='', responsable='', prioridad='media', plazo_hora=''):
        with self._conn() as conn:
            cur = conn.execute(
                'INSERT INTO acuerdos (reunion_id, texto, plazo, responsable, prioridad, plazo_hora) VALUES (?,?,?,?,?,?)',
                (reunion_id, texto, plazo, responsable, prioridad, plazo_hora),
            )
            return cur.lastrowid

    def actualizar_acuerdo(self, acuerdo_id, texto, plazo='', responsable='', prioridad='media', plazo_hora=''):
        with self._conn() as conn:
            conn.execute(
                'UPDATE acuerdos SET texto=?, plazo=?, responsable=?, prioridad=?, plazo_hora=? WHERE id=?',
                (texto, plazo, responsable, prioridad, plazo_hora, acuerdo_id),
            )

    def listar_acuerdos(self, reunion_id):
        with self._conn() as conn:
            rows = conn.execute(
                'SELECT * FROM acuerdos WHERE reunion_id=? ORDER BY created_at, id',
                (reunion_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def eliminar_acuerdo(self, acuerdo_id):
        with self._conn() as conn:
            conn.execute('DELETE FROM acuerdos WHERE id=?', (acuerdo_id,))

    def marcar_estado_acuerdo(self, acuerdo_id, estado):
        with self._conn() as conn:
            conn.execute('UPDATE acuerdos SET estado=? WHERE id=?', (estado, acuerdo_id))

    def listar_todos_acuerdos(self, estado=None, busqueda=None, limit=None, offset=0):
        hoy = datetime.now().strftime('%Y-%m-%d')
        query = '''
            SELECT a.*, r.asunto as reunion_asunto, r.fecha as reunion_fecha
            FROM acuerdos a
            JOIN reuniones r ON r.id = a.reunion_id
        '''
        conds = []
        params = []
        if estado and estado != 'todos':
            if estado == 'vencido':
                conds.append("a.estado != 'completado' AND a.plazo != '' AND a.plazo < ?")
                params.append(hoy)
            else:
                conds.append('a.estado = ?')
                params.append(estado)
        if busqueda:
            conds.append('(a.texto LIKE ? OR a.responsable LIKE ? OR r.asunto LIKE ?)')
            params += [f'%{busqueda}%'] * 3
        if conds:
            query += ' WHERE ' + ' AND '.join(conds)
        query += " ORDER BY (a.plazo = '' OR a.plazo IS NULL), a.plazo ASC"
        # Ver nota de limit=None en listar_reuniones -- mismo criterio aqui.
        if limit is not None:
            query += ' LIMIT ? OFFSET ?'
            params += [limit, offset]
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def contar_acuerdos_activos(self):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as c FROM acuerdos WHERE estado != 'completado'"
            ).fetchone()
            return row['c'] if row else 0

    def acuerdos_con_plazo_pendientes(self):
        # ultima_alerta != 'vencido' (no alerta_enviada=0) -- un acuerdo debe
        # poder seguir apareciendo aqui tras avisar "vence manana"/"vence
        # HOY", para que verificar_plazos_acuerdos() lo vuelva a notificar
        # cuando cambie de categoria. "vencido" es terminal, ahi si se deja
        # de traer. Ver utils/notificaciones.py::verificar_plazos_acuerdos.
        manana = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        with self._conn() as conn:
            rows = conn.execute('''
                SELECT a.id, a.texto, a.plazo, a.ultima_alerta, a.responsable,
                       r.asunto as reunion_asunto
                FROM acuerdos a
                JOIN reuniones r ON r.id = a.reunion_id
                WHERE a.plazo != '' AND a.ultima_alerta != 'vencido' AND a.estado != 'completado'
                  AND a.plazo <= ?
            ''', (manana,)).fetchall()
            return [dict(r) for r in rows]

    def marcar_alerta_acuerdo_enviada(self, acuerdo_id, categoria):
        with self._conn() as conn:
            conn.execute('UPDATE acuerdos SET ultima_alerta=? WHERE id=?', (categoria, acuerdo_id))
