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
    from kivy.uix.screenmanager import ScreenManager, NoTransition

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
            # FadeTransition (ShaderTransition) toma una foto (FBO) de cada
            # pantalla al tamano que tenga en ese instante y fuerza screen_in
            # a ese mismo tamano -- si el tamano real de la ventana en
            # Android todavia no se estabiliza en ese momento, esa foto mala
            # queda "pegada" en pantalla (hueco arriba, contenido tapado)
            # aunque el layout real ya este bien despues. NoTransition no usa
            # FBO ni fuerza tamanos, evita el problema de raiz.
            root.ids.sm.transition = NoTransition()
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
            from kivy.utils import platform
            if platform == 'android':
                Clock.schedule_once(self._mostrar_diagnostico_layout, 0.8)

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

        def _mostrar_diagnostico_layout(self, dt):
            """DIAGNÓSTICO TEMPORAL: muestra medidas reales de la ventana en
            el dispositivo para averiguar por qué el layout sale corrido en
            el primer arranque. Quitar una vez resuelto el bug."""
            root = self.root
            toolbar = root.ids.toolbar
            sm = root.ids.sm
            bar = root.ids.bottom_bar
            pantalla = sm.current_screen
            info = [
                f'Pantalla actual = {sm.current}',
                f'Window.size = {Window.size}',
                f'root.size = {root.size}  root.pos = {root.pos}',
                f'toolbar.size = {toolbar.size}  toolbar.pos = {toolbar.pos}',
                f'sm.size = {sm.size}  sm.pos = {sm.pos}',
                f'bottom_bar.size = {bar.size}  bottom_bar.pos = {bar.pos}',
                f'pantalla.size = {pantalla.size}  pantalla.pos = {pantalla.pos}',
            ]
            if pantalla.children:
                hijo = pantalla.children[0]
                info.append(
                    f'pantalla.children[0] ({type(hijo).__name__}) = '
                    f'size:{hijo.size} pos:{hijo.pos}'
                )
                if hasattr(hijo, 'scroll_y'):
                    info.append(f'  scroll_y = {hijo.scroll_y}')
                if hijo.children:
                    nieto = hijo.children[0]
                    info.append(
                        f'  hijo[0] ({type(nieto).__name__}) = '
                        f'size:{nieto.size} pos:{nieto.pos}'
                    )
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity
                DisplayMetrics = autoclass('android.util.DisplayMetrics')
                metrics = DisplayMetrics()
                activity.getWindowManager().getDefaultDisplay().getRealMetrics(metrics)
                info.append(
                    f'Android real display px = {metrics.widthPixels} x '
                    f'{metrics.heightPixels}, density={metrics.density}'
                )

                Rect = autoclass('android.graphics.Rect')
                rect = Rect()
                decor = activity.getWindow().getDecorView()
                decor.getWindowVisibleDisplayFrame(rect)
                info.append(
                    f'decorView visible frame = top:{rect.top} '
                    f'bottom:{rect.bottom} left:{rect.left} right:{rect.right}'
                )
                info.append(
                    f'decorView size = {decor.getWidth()} x {decor.getHeight()}'
                )

                resources = activity.getResources()
                rid_status = resources.getIdentifier('status_bar_height', 'dimen', 'android')
                status_h = resources.getDimensionPixelSize(rid_status) if rid_status > 0 else -1
                rid_nav = resources.getIdentifier('navigation_bar_height', 'dimen', 'android')
                nav_h = resources.getDimensionPixelSize(rid_nav) if rid_nav > 0 else -1
                info.append(f'status_bar_height px = {status_h}, navigation_bar_height px = {nav_h}')

                AndroidR = autoclass('android.R$id')
                content_view = activity.findViewById(AndroidR.content)
                info.append(f'content view size = {content_view.getWidth()} x {content_view.getHeight()}')
            except Exception as e:
                info.append(f'Error leyendo metrics de Android: {e}')

            texto = '\n'.join(info)
            dialog = MDDialog(
                title='Diagnóstico de layout (temporal)',
                text=texto,
                buttons=[MDFlatButton(text='OK', on_release=lambda x: dialog.dismiss())],
            )
            dialog.open()

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
                sm.current = screen_name
            if screen_name != 'login':
                bar = self.root.ids.bottom_bar
                bar.opacity = 1
                bar.size_hint_y = None
                bar.height = '56dp'
            from kivy.utils import platform
            if platform == 'android' and screen_name != 'login':
                Clock.schedule_once(self._mostrar_diagnostico_layout, 0.3)

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
            sm.current = self._PARENT_SCREEN.get(sm.current, 'dashboard')

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
