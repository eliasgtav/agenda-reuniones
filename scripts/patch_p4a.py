import re

base = '.buildozer/android/platform/python-for-android/pythonforandroid/recipes'

# hostpython3: Python 3.14.2 -> 3.12.9
# ATENCION: el archivo usa comillas DOBLES: version = "3.14.2"
path = f'{base}/hostpython3/__init__.py'
c = open(path).read()

# Reemplazo exacto con comillas dobles
old_ver = '    version = "3.14.2"'
new_ver = '    version = "3.12.9"'
if old_ver in c:
    c = c.replace(old_ver, new_ver, 1)
    print('hostpython3: version reemplazada (doble comilla) 3.14.2 -> 3.12.9')
else:
    # Fallback: cualquier quote style
    c = re.sub(r'version\s*=\s*[\'"][0-9.]+[\'"]', 'version = "3.12.9"', c, count=1)
    print('hostpython3: version reemplazada por regex')

# Limpiar sha512sum si existe
c = re.sub(r'sha512sum\s*=\s*[\'"][^\'\"]*[\'"]', "sha512sum = ''", c)
# Limpiar patches para evitar fallos con parches de 3.14
c = re.sub(r'patches\s*=\s*\[[\s\S]*?\]', 'patches = []', c, count=1)
open(path, 'w').write(c)
print('hostpython3 parcheado a 3.12.9')

# python3: ya funciona con la subclase _Py312Fix
# Solo asegurar que el reemplazo exacto de version tambien se haga
path = f'{base}/python3/__init__.py'
c = open(path).read()

old_ver = "    version = '3.14.2'"
new_ver = "    version = '3.12.9'"
if old_ver in c:
    c = c.replace(old_ver, new_ver, 1)
    print('python3: version reemplazada (comilla simple) 3.14.2 -> 3.12.9')
else:
    c = re.sub(r'version\s*=\s*[\'"][0-9.]+[\'"]', "version = '3.12.9'", c, count=1)
    print('python3: version reemplazada por regex')

# Subclase override para garantizar version 3.12.9 y omitir patches de 3.14
c = c.rstrip('\n') + '\n'
c += '\nclass _Py312Fix(Python3Recipe):\n'
c += '    version = "3.12.9"\n'
c += '    def apply_patches(self, arch, build_dir=None): pass\n'
c += 'Python3Recipe = _Py312Fix\n'
c += 'recipe = Python3Recipe()\n'
open(path, 'w').write(c)
print('python3 parcheado a 3.12.9')

# AndroidManifest: deshabilitar HWUI en la Activity SDL2
# Crash en Android 15 Honor: pthread_mutex_lock on destroyed mutex (hwuiTask1)
# SDL2 usa OpenGL ES directo; HWUI interfiere causando SIGABRT
manifest = '.buildozer/android/platform/python-for-android/pythonforandroid/bootstraps/sdl2/build/templates/AndroidManifest.tmpl.xml'
try:
    c = open(manifest).read()
    if 'android:hardwareAccelerated="false"' not in c:
        c = c.replace(
            'android:name="org.kivy.android.PythonActivity"',
            'android:name="org.kivy.android.PythonActivity"\n        android:hardwareAccelerated="false"',
            1
        )
        open(manifest, 'w').write(c)
        print('AndroidManifest: hardwareAccelerated=false aplicado')
    else:
        print('AndroidManifest: ya tiene hardwareAccelerated=false')
except Exception as e:
    print(f'AndroidManifest patch fallido: {e}')
