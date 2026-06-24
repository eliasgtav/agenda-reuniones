"""
Parches para compilar con p4a master + Kivy 2.3.0:

1. Python 3.14 → 3.12.9: p4a master trae Python 3.14 que rompe la API C
   de Kivy 2.3.0 ("too few arguments"). Se parchea a 3.12.9 que sí es
   compatible y compila correctamente.

2. HWUI fix (Android 15): android:hardwareAccelerated="false" en la Activity
   para evitar crash pthread_mutex_lock con SDL2 + OpenGL ES.
"""

import re
import os

base = '.buildozer/android/platform/python-for-android/pythonforandroid/recipes'

# --- 1. hostpython3: parchear version a 3.12.9 ---
path = f'{base}/hostpython3/__init__.py'
c = open(path).read()
c = re.sub(r'version\s*=\s*[\'"][0-9.]+[\'"]', 'version = "3.12.9"', c, count=1)
c = re.sub(r'sha512sum\s*=\s*[\'"][^\'\"]*[\'"]', "sha512sum = ''", c)
c = re.sub(r'patches\s*=\s*\[[\s\S]*?\]', 'patches = []', c, count=1)
open(path, 'w').write(c)
print('hostpython3 parcheado a 3.12.9')

# --- 2. python3: parchear version a 3.12.9 ---
path = f'{base}/python3/__init__.py'
c = open(path).read()
c = re.sub(r"version\s*=\s*['\"][0-9.]+['\"]", "version = '3.12.9'", c, count=1)
c = re.sub(r"sha512sum\s*=\s*['\"][^'\"]*['\"]", "sha512sum = ''", c)

c = c.rstrip('\n') + '\n'
c += '\nclass _Py312Fix(Python3Recipe):\n'
c += '    version = "3.12.9"\n'
c += '    def apply_patches(self, arch, build_dir=None): pass\n'
c += 'Python3Recipe = _Py312Fix\n'
c += 'recipe = Python3Recipe()\n'
open(path, 'w').write(c)
print('python3 parcheado a 3.12.9')

# --- 3. AndroidManifest: HWUI fix (Android 15) ---
bootstrap_base = '.buildozer/android/platform/python-for-android/pythonforandroid/bootstraps'
candidates = [
    os.path.join(bootstrap_base, '_sdl_common/build/templates/AndroidManifest.tmpl.xml'),
    os.path.join(bootstrap_base, 'sdl2/build/templates/AndroidManifest.tmpl.xml'),
]

for manifest in candidates:
    if os.path.exists(manifest):
        c = open(manifest).read()
        if 'android:hardwareAccelerated="false"' not in c:
            c = c.replace(
                'android:name="org.kivy.android.PythonActivity"',
                'android:name="org.kivy.android.PythonActivity"\n        android:hardwareAccelerated="false"',
                1,
            )
            open(manifest, 'w').write(c)
            print(f'HWUI fix aplicado: {manifest}')
        else:
            print(f'HWUI fix ya presente: {manifest}')
        break
else:
    print('ADVERTENCIA: AndroidManifest no encontrado')
    for p in candidates:
        print(f'  {p} → existe={os.path.exists(p)}')
