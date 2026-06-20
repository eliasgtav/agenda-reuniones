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

# python3: subclase que fuerza version 3.12.9
# NOTA: RecipeMeta transforma 'version = ...' en '_version = ...' al definir la clase.
# La @property 'version' en Recipe retorna self._version, por eso funciona sin setter.
# NO se puede hacer recipe.version = "..." en instancias (read-only property).
path = f'{base}/python3/__init__.py'
c = open(path).read()

# Reemplazo exacto de la version en la clase original (por si acaso)
old_ver = "    version = '3.14.2'"
new_ver = "    version = '3.12.9'"
if old_ver in c:
    c = c.replace(old_ver, new_ver, 1)
    print('python3: version reemplazada 3.14.2 -> 3.12.9 (exacto)')
else:
    c = re.sub(r"    version = '[0-9.]+'", "    version = '3.12.9'", c, count=1)
    print('python3: version reemplazada por regex')

# Agregar subclase que fuerza version 3.12.9 y omite patches especificos de 3.14
# RecipeMeta convierte 'version = "3.12.9"' -> '_version = "3.12.9"' automaticamente
c = c.rstrip('\n') + '\n'
c += '\nclass _Py312Fix(Python3Recipe):\n'
c += '    version = "3.12.9"\n'
c += '    def apply_patches(self, arch, build_dir=None): pass\n'
c += 'Python3Recipe = _Py312Fix\n'
c += 'recipe = Python3Recipe()\n'
open(path, 'w').write(c)
print('python3 parcheado a 3.12.9')
