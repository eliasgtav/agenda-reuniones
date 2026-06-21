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
    '/sdcard/Android/data/com.eliasgt.agenda.agendareuniones/files/agenda_crash.txt',
    '/sdcard/agenda_crash.txt',
]

def _write_crash(err):
    for path in _CRASH_LOG_PATHS:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(err)
            return path
        except Exception:
            continue
    return None

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
    from kivy.uix.screenmanager import ScreenManager, FadeTransition
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
            root.ids.sm.transition = FadeTransition()
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
        _show_crash_screen(_IMPORT_ERROR)
    else:
        try:
            _AgendaApp().run()
        except Exception:
            err = traceback.format_exc()
            _write_crash(err)
            if platform == 'android':
                _show_crash_screen(err)
            else:
                raise
