import re

base = '.buildozer/android/platform/python-for-android/pythonforandroid/recipes'

# hostpython3: Python 3.14 -> 3.12.9
path = f'{base}/hostpython3/__init__.py'
c = open(path).read()
c = re.sub(r"version = '[0-9.]+'", "version = '3.12.9'", c, count=1)
c = re.sub(r"sha512sum = '[^']*'", "sha512sum = ''", c)
c = re.sub(r'patches\s*=\s*\[[\s\S]*?\]', 'patches = []', c, count=1)
open(path, 'w').write(c)
print('hostpython3 parcheado a 3.12.9')

# python3: cambiar version con reemplazo exacto
path = f'{base}/python3/__init__.py'
c = open(path).read()

# Reemplazo exacto (no regex) para evitar errores
old_ver = "    version = '3.14.2'"
new_ver = "    version = '3.12.9'"
if old_ver in c:
    c = c.replace(old_ver, new_ver, 1)
    print('python3: reemplazo exacto OK (3.14.2 -> 3.12.9)')
else:
    # Fallback con regex mas amplio
    c = re.sub(r"    version = '[0-9.]+'", "    version = '3.12.9'", c, count=1)
    print('python3: reemplazo por regex (version exacta no encontrada)')

# Override al final: subclase que fuerza version 3.12.9 y cancela patches 3.14
c = c.rstrip('\n') + '\n'
c += '\nclass _Py312Fix(Python3Recipe):\n'
c += '    version = "3.12.9"\n'
c += '    sha512sum = ""\n'
c += '    patches = []\n'
c += '    def apply_patches(self, arch, build_dir=None): pass\n'
c += 'Python3Recipe = _Py312Fix\n'
c += 'recipe = Python3Recipe()\n'
c += 'recipe.version = "3.12.9"\n'
open(path, 'w').write(c)

# Verificacion: mostrar lineas con 'version' y las ultimas 12 lineas
with open(path) as f:
    v = f.read()
ver_lines = [l for l in v.split('\n') if 'version' in l and "'" in l and '3.' in l]
print(f'Lineas con version en archivo: {ver_lines}')
print('Ultimas 12 lineas del archivo python3:')
for line in v.split('\n')[-12:]:
    print(repr(line))
print('python3 parcheado a 3.12.9')
