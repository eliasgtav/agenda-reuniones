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
                    alerta_enviada INTEGER DEFAULT 0,
                    created_at  TEXT    DEFAULT (datetime('now','localtime')),
                    FOREIGN KEY (reunion_id) REFERENCES reuniones(id) ON DELETE CASCADE
                );
            ''')

    # ── Reuniones ──────────────────────────────────────────────────────────────

    def crear_reunion(self, asunto, fecha, hora, lugar='', notas='', tipos_alerta=None):
        with self._conn() as conn:
            cur = conn.execute(
                'INSERT INTO reuniones (asunto, fecha, hora, lugar, notas) VALUES (?,?,?,?,?)',
                (asunto, fecha, hora, lugar, notas),
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

    def listar_reuniones(self, estado=None, busqueda=None):
        query = 'SELECT * FROM reuniones'
        params = []
        conds = []
        if estado and estado != 'todas':
            conds.append('estado=?')
            params.append(estado)
        if busqueda:
            conds.append('(asunto LIKE ? OR lugar LIKE ?)')
            params += [f'%{busqueda}%', f'%{busqueda}%']
        if conds:
            query += ' WHERE ' + ' AND '.join(conds)
        query += ' ORDER BY fecha DESC, hora DESC'
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def eliminar_reunion(self, reunion_id):
        with self._conn() as conn:
            conn.execute('DELETE FROM reuniones WHERE id=?', (reunion_id,))

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
            conn.execute('DELETE FROM archivos WHERE id=?', (archivo_id,))

    # ── Alertas ────────────────────────────────────────────────────────────────

    def auto_cancelar_vencidas(self):
        # Solo cancela reuniones que lleven más de 1 hora sin iniciarse
        limite = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')
        with self._conn() as conn:
            vencidas = conn.execute('''
                SELECT asunto FROM reuniones
                WHERE estado = 'pendiente'
                  AND (fecha || ' ' || hora) < ?
            ''', (limite,)).fetchall()
            if vencidas:
                conn.execute('''
                    UPDATE reuniones
                    SET estado = 'cancelada',
                        updated_at = datetime('now','localtime')
                    WHERE estado = 'pendiente'
                      AND (fecha || ' ' || hora) < ?
                ''', (limite,))
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

    def guardar_acuerdo(self, reunion_id, texto, plazo=''):
        with self._conn() as conn:
            cur = conn.execute(
                'INSERT INTO acuerdos (reunion_id, texto, plazo) VALUES (?,?,?)',
                (reunion_id, texto, plazo),
            )
            return cur.lastrowid

    def listar_acuerdos(self, reunion_id):
        with self._conn() as conn:
            rows = conn.execute(
                'SELECT * FROM acuerdos WHERE reunion_id=? ORDER BY created_at',
                (reunion_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def eliminar_acuerdo(self, acuerdo_id):
        with self._conn() as conn:
            conn.execute('DELETE FROM acuerdos WHERE id=?', (acuerdo_id,))

    def acuerdos_con_plazo_pendientes(self):
        hoy = datetime.now().strftime('%Y-%m-%d')
        manana = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        with self._conn() as conn:
            rows = conn.execute('''
                SELECT a.id, a.texto, a.plazo, a.alerta_enviada,
                       r.asunto as reunion_asunto
                FROM acuerdos a
                JOIN reuniones r ON r.id = a.reunion_id
                WHERE a.plazo != '' AND a.alerta_enviada = 0
                  AND a.plazo <= ?
            ''', (manana,)).fetchall()
            return [dict(r) for r in rows]

    def marcar_alerta_acuerdo_enviada(self, acuerdo_id):
        with self._conn() as conn:
            conn.execute('UPDATE acuerdos SET alerta_enviada=1 WHERE id=?', (acuerdo_id,))
