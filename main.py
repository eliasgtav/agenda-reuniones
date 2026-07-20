# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
# Agenda de Reuniones de Trabajo — versión 1.0
import os
import sys
import traceback

os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
if sys.platform == 'win32':
    os.environ.setdefault('KIVY_GL_BACKEND', 'angle_sdl2')

# Captura TEMPRANA de cualquier crash (incluyendo errores de import)
# Escribe en el almacenamiento externo con ámbito (accesible desde el gestor de archivos)
_CRASH_LOG_PATHS = [
    '/data/data/com.eliasgt.agenda.agendareuniones/files/agenda_crash.txt',
    '/data/user/0/com.eliasgt.agenda.agendareuniones/files/agenda_crash.txt',
    '/sdcard/Android/data/com.eliasgt.agenda.agendareuniones/files/agenda_crash.txt',
    '/sdcard/agenda_crash.txt',
]

def _write_crash(err):
    paths = list(_CRASH_LOG_PATHS)
    try:
        import kivy.app
        app = kivy.app.App.get_running_app()
        if app and hasattr(app, 'user_data_dir'):
            paths.insert(0, os.path.join(app.user_data_dir, 'agenda_crash.txt'))
    except Exception:
        pass
    for path in paths:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(err)
            return path
        except Exception:
            continue
    return None


def _android_show_crash(err):
    """Muestra el crash como AlertDialog nativo de Android (siempre visible)."""
    try:
        from android.runnable import run_on_ui_thread
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        AlertBuilder = autoclass('android.app.AlertDialog$Builder')

        msg = ('CRASH en Agenda App\n\n' + err)[-2000:]

        # AlertDialog.Builder.setTitle/setMessage tienen overloads (int) y
        # (CharSequence): pasar un str de Python puede fallar a resolver la
        # sobrecarga en pyjnius ("No methods called setTitle... matching
        # your arguments"). Envolver en java.lang.String lo desambigua.
        JString = autoclass('java.lang.String')

        @run_on_ui_thread
        def _show():
            activity = PythonActivity.mActivity
            dlg = AlertBuilder(activity)
            dlg.setTitle(JString('ERROR - Agenda App'))
            dlg.setMessage(JString(msg))
            dlg.setCancelable(False)
            dlg.setPositiveButton(JString('OK'), None)
            dlg.create().show()

        _show()
        import time
        time.sleep(300)
    except Exception:
        _show_crash_screen(err)


def _show_crash_screen(err):
    """Muestra el traceback en pantalla si Kivy ya está disponible."""
    try:
        from kivy.base import runTouchApp
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.label import Label
        lbl = Label(
            text=err,
            text_size=(None, None),
            size_hint_y=None,
            font_size='12sp',
        )
        lbl.bind(texture_size=lambda i, v: setattr(i, 'height', v[1]))
        sv = ScrollView()
        sv.add_widget(lbl)
        runTouchApp(sv)
    except Exception:
        pass


_IMPORT_ERROR = None
_AgendaApp = None
_KV = None

try:
    from kivy.lang import Builder
    from kivy.clock import Clock
    from kivy.core.window import Window
    from kivy.uix.screenmanager import ScreenManager, NoTransition, FadeTransition

    # Evita que el teclado táctil tape el campo que se está editando
    # (p.ej. "Notas adicionales" y los botones bajo él).
    Window.softinput_mode = 'below_target'
    from kivymd.app import MDApp
    from kivymd.uix.button import MDFlatButton
    from kivymd.uix.dialog import MDDialog

    from database import Database
    from utils.notificaciones import NotificacionesManager
    from screens.dashboard_screen import DashboardScreen
    from screens.nueva_reunion_screen import NuevaReunionScreen
    from screens.lista_reuniones_screen import ListaReunionesScreen
    from screens.detalle_reunion_screen import DetalleReunionScreen
    from screens.perfil_screen import PerfilScreen
    from screens.login_screen import LoginScreen
    from screens.en_reunion_screen import EnReunionScreen

    _KV = '''
MDBoxLayout:
    orientation: 'vertical'

    MDTopAppBar:
        id: toolbar
        title: "Agenda de Reuniones"
        elevation: 4
        right_action_items:
            [
            ["weather-night", lambda x: app.toggle_dark_mode(), "Modo oscuro"],
            ["home", lambda x: app.go_to("dashboard"), "Inicio"]
            ]

    ScreenManager:
        id: sm

        DashboardScreen:
            name: "dashboard"

        NuevaReunionScreen:
            name: "nueva_reunion"

        ListaReunionesScreen:
            name: "lista_reuniones"

        DetalleReunionScreen:
            name: "detalle_reunion"

        PerfilScreen:
            name: "perfil"

        LoginScreen:
            name: "login"

        EnReunionScreen:
            name: "en_reunion"

    MDBoxLayout:
        id: bottom_bar
        size_hint_y: None
        height: "56dp"
        md_bg_color: app.theme_cls.primary_color

        MDIconButton:
            icon: "home"
            theme_icon_color: "Custom"
            icon_color: 1,1,1,1
            on_release: app.go_to("dashboard")

        MDIconButton:
            icon: "plus-circle-outline"
            theme_icon_color: "Custom"
            icon_color: 1,1,1,1
            on_release: app.go_to("nueva_reunion")

        MDIconButton:
            icon: "format-list-bulleted"
            theme_icon_color: "Custom"
            icon_color: 1,1,1,1
            on_release: app.go_to("lista_reuniones")

        MDIconButton:
            icon: "account-circle"
            theme_icon_color: "Custom"
            icon_color: 1,1,1,1
            on_release: app.go_to("perfil")
'''

    class AgendaApp(MDApp):
        reunion_activa_id = None

        def build(self):
            self.title = 'Agenda de Reuniones'
            self.theme_cls.primary_palette = 'Blue'
            self.theme_cls.accent_palette = 'Amber'
            self.theme_cls.theme_style = 'Light'

            self.db = Database()
            self.notif_manager = NotificacionesManager(self.db)

            root = Builder.load_string(_KV)
            # ScreenManager solo agrega de verdad al arbol de widgets la
            # PRIMERA pantalla (dashboard, la primera del KV) -- las otras 6
            # quedan sin agregar hasta su primera navegacion (ver
            # ScreenManager.add_widget/on_current en kivy/uix/screenmanager.py).
            # FadeTransition (ShaderTransition.add_screen) fuerza
            # screen_in.size = screen_out.size y toma una foto FBO en ese
            # mismo instante -- si esa primera navegacion es tambien la
            # primera vez que la pantalla se agrega al arbol, la foto queda
            # tomada ANTES de que su contenido (MDScrollView, alturas
            # adaptativas) termine su propio primer layout: hueco pegado.
            # NoTransition.add_screen no fuerza tamano ni toma foto, asi que
            # no tiene ese problema. Por eso: primera visita a cada pantalla
            # usa NoTransition (seguro), visitas siguientes (pantalla ya
            # agregada y con layout resuelto) usan FadeTransition (fluido,
            # sin destello). Ver _ir_a() mas abajo.
            root.ids.sm.transition = NoTransition()
            # OJO: no pre-marcar 'dashboard' como visitada aqui. Aunque se
            # agrega al arbol de forma sincrona arriba, login_screen.py
            # navega a dashboard con app.go_to('dashboard') justo despues de
            # registrarse -- esa es la PRIMERA VEZ que el usuario realmente
            # VE dashboard, y si ya estuviera marcada como visitada, _ir_a()
            # elegiria FadeTransition ahi mismo, cayendo en la misma carrera
            # FBO-antes-de-layout que se esta evitando en las demas
            # pantallas (confirmado con captura: hueco en dashboard justo
            # al salir del login, con NoTransition en todas las demas
            # pantallas funcionando bien).
            self._pantallas_visitadas = set()
            return root

        def on_start(self):
            from utils.config import cargar
            config = cargar()
            if not config.get('registrado'):
                self.root.ids.sm.current = 'login'
                self.root.ids.bottom_bar.opacity = 0
                self.root.ids.bottom_bar.size_hint_y = None
                self.root.ids.bottom_bar.height = 0
            Clock.schedule_interval(self._check_alertas, 60)
            Clock.schedule_once(self._check_alertas, 2)
            for delay in (0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0):
                Clock.schedule_once(self._reajustar_layout, delay)
            # Los reintentos de arriba tienen un limite fijo de 1s -- en un
            # arranque en frio particularmente lento (cache de disco fria,
            # primera vez que Android compila/carga todo) Window.size puede
            # tardar mas que eso en estabilizarse, y ese limite se queda
            # corto (hueco arriba, MDScrollView mal calculado). En vez de
            # adivinar un tiempo mas largo, reaccionar directamente cada vez
            # que Window.size CAMBIE de verdad, sin limite de tiempo -- asi
            # no importa cuanto tarde ese arranque en particular.
            Window.bind(size=self._on_window_resize)

        def _on_window_resize(self, window, size):
            self._reajustar_layout(0)
            pantalla = self.root.ids.sm.current_screen
            if hasattr(pantalla, '_forzar_scroll_arriba'):
                pantalla._forzar_scroll_arriba()

        def _ir_a(self, screen_name):
            sm = self.root.ids.sm
            primera_vez = screen_name not in self._pantallas_visitadas
            if primera_vez:
                sm.transition = NoTransition()
            else:
                # ShaderTransition.clearcolor (clase base de FadeTransition)
                # define de que color se limpia el FBO donde se "fotografia"
                # cada pantalla para el crossfade -- por defecto en Kivy es
                # [0, 0, 0, 1] (negro), sin relacion con el tema de la app.
                # Ninguna pantalla pinta su propio fondo (dependen del
                # Window.clearcolor global que KivyMD ya mantiene sincronizado
                # con el tema claro/oscuro), asi que cualquier area no
                # cubierta por widgets dentro de esa foto se veia negra
                # durante el crossfade (confirmado con capturas: fondo blanco
                # en la primera visita con NoTransition -- sin Fbo, son
                # widgets vivos sobre el Window real -- y fondo negro en
                # visitas siguientes con FadeTransition). Se usa el mismo
                # color que ya tiene Window.clearcolor en este momento.
                sm.transition = FadeTransition(clearcolor=Window.clearcolor)
            self._pantallas_visitadas.add(screen_name)
            sm.current = screen_name

        def _reajustar_layout(self, dt):
            # En el arranque en frío en Android, Window a veces reporta un
            # tamaño provisional durante varios cuadros antes de que el
            # sistema descuente la barra de estado/navegación, y el layout
            # queda calculado con ese tamaño incorrecto (contenido corrido,
            # botones tapados). Reintentar varias veces durante el primer
            # segundo (no solo una vez) cubre la condición de carrera sin
            # importar en qué cuadro se estabiliza el tamaño real.
            self.root.size = Window.size
            self.root.do_layout()

        def _check_alertas(self, *args):
            canceladas = self.db.auto_cancelar_vencidas()
            if canceladas:
                self._mostrar_canceladas(canceladas)
            self.notif_manager.verificar_alertas()

        def _mostrar_canceladas(self, asuntos):
            lista = '\n'.join(f'• {a}' for a in asuntos)
            dialog = MDDialog(
                title='Reuniones canceladas automáticamente',
                text=f'Las siguientes reuniones no se realizaron y fueron canceladas:\n\n{lista}',
                buttons=[MDFlatButton(text='ACEPTAR', on_release=lambda x: dialog.dismiss())],
            )
            dialog.open()

        def toggle_dark_mode(self):
            self.theme_cls.theme_style = (
                'Dark' if self.theme_cls.theme_style == 'Light' else 'Light'
            )

        def go_to(self, screen_name):
            sm = self.root.ids.sm
            if sm.current != screen_name:
                self._ir_a(screen_name)
            if screen_name != 'login':
                bar = self.root.ids.bottom_bar
                bar.opacity = 1
                bar.size_hint_y = None
                bar.height = '56dp'

        _PARENT_SCREEN = {
            'lista_reuniones': 'dashboard',
            'nueva_reunion':   'lista_reuniones',
            'detalle_reunion': 'lista_reuniones',
            'perfil':          'dashboard',
            'en_reunion':      'detalle_reunion',
            'login':           'dashboard',
        }

        def go_back(self):
            sm = self.root.ids.sm
            self._ir_a(self._PARENT_SCREEN.get(sm.current, 'dashboard'))

        def actualizar_foto_dashboard(self):
            try:
                dashboard = self.root.ids.sm.get_screen('dashboard')
                dashboard.actualizar_perfil()
            except Exception:
                pass

    _AgendaApp = AgendaApp

except Exception:
    _IMPORT_ERROR = traceback.format_exc()


if __name__ == '__main__':
    from kivy.utils import platform

    if _IMPORT_ERROR:
        _write_crash(_IMPORT_ERROR)
        if platform == 'android':
            _android_show_crash(_IMPORT_ERROR)
        else:
            _show_crash_screen(_IMPORT_ERROR)
    else:
        try:
            _AgendaApp().run()
        except Exception:
            err = traceback.format_exc()
            _write_crash(err)
            if platform == 'android':
                _android_show_crash(err)
            else:
                raise
