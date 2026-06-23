"""
Parches para p4a master al compilar con Kivy 2.3.0:

1. Python 3.14 -> 3.12.9: p4a master trae hostpython3/python3 apuntando a
   Python 3.14.x que aún no es estable para Android. Parcheamos a 3.12.9.

2. HWUI fix (Android 15 Honor): android:hardwareAccelerated="false" en Activity
   para evitar crash pthread_mutex_lock en hwuiTask1 con SDL2 + OpenGL ES.
"""

import re

base = '.buildozer/android/platform/python-for-android/pythonforandroid/recipes'

# --- 1. hostpython3: parchear version a 3.12.9 ---
path = f'{base}/hostpython3/__init__.py'
c = open(path).read()

old_ver = '    version = "3.14.2"'
new_ver = '    version = "3.12.9"'
if old_ver in c:
    c = c.replace(old_ver, new_ver, 1)
    print('hostpython3: version reemplazada 3.14.2 -> 3.12.9')
else:
    c = re.sub(r'version\s*=\s*[\'"][0-9.]+[\'"]', 'version = "3.12.9"', c, count=1)
    print('hostpython3: version reemplazada por regex')

c = re.sub(r'sha512sum\s*=\s*[\'"][^\'\"]*[\'"]', "sha512sum = ''", c)
c = re.sub(r'patches\s*=\s*\[[\s\S]*?\]', 'patches = []', c, count=1)
open(path, 'w').write(c)
print('hostpython3 parcheado a 3.12.9')

# --- 2. python3: parchear version a 3.12.9 ---
path = f'{base}/python3/__init__.py'
c = open(path).read()

old_ver = "    version = '3.14.2'"
new_ver = "    version = '3.12.9'"
if old_ver in c:
    c = c.replace(old_ver, new_ver, 1)
    print('python3: version reemplazada 3.14.2 -> 3.12.9')
else:
    c = re.sub(r'version\s*=\s*[\'"][0-9.]+[\'"]', "version = '3.12.9'", c, count=1)
    print('python3: version reemplazada por regex')

c = c.rstrip('\n') + '\n'
c += '\nclass _Py312Fix(Python3Recipe):\n'
c += '    version = "3.12.9"\n'
c += '    def apply_patches(self, arch, build_dir=None): pass\n'
c += 'Python3Recipe = _Py312Fix\n'
c += 'recipe = Python3Recipe()\n'
open(path, 'w').write(c)
print('python3 parcheado a 3.12.9')

# --- 3. AndroidManifest: HWUI fix (Android 15 Honor) ---
# _sdl_common es la ruta en p4a master (antes era bootstraps/sdl2/...)
manifest = '.buildozer/android/platform/python-for-android/pythonforandroid/bootstraps/_sdl_common/build/templates/AndroidManifest.tmpl.xml'

try:
    c = open(manifest).read()
    if 'android:hardwareAccelerated="false"' not in c:
        c = c.replace(
            'android:name="org.kivy.android.PythonActivity"',
            'android:name="org.kivy.android.PythonActivity"\n        android:hardwareAccelerated="false"',
            1
        )
        open(manifest, 'w').write(c)
        print('AndroidManifest: hardwareAccelerated=false aplicado (fix Android 15 Honor)')
    else:
        print('AndroidManifest: ya tiene hardwareAccelerated=false')
except Exception as e:
    print(f'AndroidManifest patch fallido: {e}')
