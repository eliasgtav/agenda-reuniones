"""
Parches para compilar con p4a master + Kivy 2.3.0:

1. Python 3.14 → 3.12.9: p4a master trae Python 3.14 que rompe la API C
   de Kivy 2.3.0 ("too few arguments"). Se parchea a 3.12.9 que sí es
   compatible y compila correctamente.

Nota: el parche android:hardwareAccelerated="false" fue eliminado porque
SDL2 2.30.11 (usado por p4a master actual) ya tiene el fix para Android 15
(pthread_mutex_lock). Mantenerlo rompía la creación del contexto EGL.
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
