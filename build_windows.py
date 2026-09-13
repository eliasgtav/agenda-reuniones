# © 2024 Elías Gaytan Alvino — Todos los derechos reservados.
"""Compila el ejecutable de Windows con PyInstaller.

Por que no es un simple `pyinstaller main.py`: Kivy en Windows carga OpenGL
via ANGLE (libEGL.dll/libGLESv2.dll/d3dcompiler_47.dll) y SDL2 (SDL2.dll y
sus companeros), pero esos .dll NO viven dentro del paquete Python de
kivy_deps -- viven en `sys.prefix/share/<angle|sdl2|glew>/bin` y kivy los
encuentra en tiempo de ejecucion importando dinamicamente cada submodulo de
`kivy_deps` (ver kivy/__init__.py, pkgutil.iter_modules). PyInstaller no
detecta ese patron con su analisis estatico normal, asi que sin agregar
estos .dll a mano el ejecutable compila "bien" pero se cae al abrir con
"Could not initialize OpenGL / GLES library". Aparte, KivyMD registra sus
widgets (MDTopAppBar y compania) de forma dinamica por submodulo -- sin
`--collect-all kivymd` el ejecutable revienta con
`FactoryException: No class named <MDTopAppBar>` al cargar el primer KV.

Ambos problemas se confirmaron compilando de verdad (no son teoricos) y
este script existe para no volver a pisarlos."""
import os
import sys
import shutil

try:
    import kivy_deps.angle
    import kivy_deps.sdl2
    import kivy_deps.glew
except ImportError:
    print('Instala primero las dependencias: pip install -r requirements.txt kivy_deps.angle kivy_deps.sdl2 kivy_deps.glew pyinstaller')
    sys.exit(1)


def _dlls_de(dep_bins):
    """dep_bins es una lista de carpetas 'share/<paquete>/bin' -- junta
    todos los .dll que haya en ellas (deja fuera los .txt de licencia)."""
    rutas = []
    for carpeta in dep_bins:
        if not os.path.isdir(carpeta):
            continue
        for nombre in os.listdir(carpeta):
            if nombre.lower().endswith('.dll'):
                rutas.append(os.path.join(carpeta, nombre))
    return rutas


def main():
    aqui = os.path.dirname(os.path.abspath(__file__))
    os.chdir(aqui)

    for carpeta in ('build', 'dist'):
        ruta = os.path.join(aqui, carpeta)
        if os.path.isdir(ruta):
            shutil.rmtree(ruta, ignore_errors=True)
    spec = os.path.join(aqui, 'AgendaReuniones.spec')
    if os.path.isfile(spec):
        os.remove(spec)

    dlls = (
        _dlls_de(kivy_deps.angle.dep_bins)
        + _dlls_de(kivy_deps.sdl2.dep_bins)
        + _dlls_de(kivy_deps.glew.dep_bins)
    )
    if not dlls:
        print('ADVERTENCIA: no se encontraron los .dll de angle/sdl2/glew -- '
              'revisa que kivy_deps.angle/sdl2/glew esten instalados con pip '
              '(no solo kivy).')

    args = [
        '--onefile', '--windowed', '--noconfirm',
        '--name', 'AgendaReuniones',
        '--add-data', 'screens;screens',
        '--add-data', 'utils;utils',
        '--collect-all', 'kivymd',
        '--hidden-import', 'plyer',
        '--hidden-import', 'openpyxl',
        '--hidden-import', 'pyttsx3',
    ]
    icono = os.path.join(aqui, 'data', 'icon.png')
    if os.path.isfile(icono):
        args += ['--icon', icono]
    for dll in dlls:
        # Los .dll van directo a la raiz del paquete (junto al .exe una vez
        # descomprimido) -- ahi Windows los encuentra solo, sin depender de
        # que kivy_deps alcance a configurar el PATH dentro del ejecutable
        # empaquetado.
        args += ['--add-binary', f'{dll};.']
    args.append('main.py')

    os.environ.setdefault('KIVY_GL_BACKEND', 'angle_sdl2')
    os.environ.setdefault('KIVY_NO_ARGS', '1')

    from PyInstaller.__main__ import run as pyinstaller_run
    pyinstaller_run(args)

    exe = os.path.join(aqui, 'dist', 'AgendaReuniones.exe')
    if os.path.isfile(exe):
        print(f'\nListo: {exe}')
    else:
        print('\nLa compilacion parece haber fallado -- revisa el log de arriba.')
        sys.exit(1)


if __name__ == '__main__':
    main()
