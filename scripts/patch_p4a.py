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

# python3: override version y apply_patches
path = f'{base}/python3/__init__.py'
c = open(path).read()
c = re.sub(r"version = '[0-9.]+'", "version = '3.12.9'", c, count=1)
c = re.sub(r"sha512sum = '[^']*'", "sha512sum = ''", c)
c += (
    '\nclass _Py312Fix(Python3Recipe):\n'
    '    version = "3.12.9"\n'
    '    sha512sum = ""\n'
    '    patches = []\n'
    '    def apply_patches(self, arch, build_dir=None): pass\n'
    'Python3Recipe = _Py312Fix\n'
    'recipe = Python3Recipe()\n'
)
open(path, 'w').write(c)
print('python3 parcheado a 3.12.9')
