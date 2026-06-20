from pythonforandroid.recipes.python3 import Python3Recipe as _Base


class Python3Recipe(_Base):
    version = '3.12.9'
    sha512sum = ''  # skip checksum — pinned for Kivy 2.3.0 / Cython 0.29 compatibility


recipe = Python3Recipe()
