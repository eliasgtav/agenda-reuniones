from pythonforandroid.recipes.hostpython3 import HostPython3Recipe as _Base


class HostPython3Recipe(_Base):
    version = '3.12.9'
    sha512sum = ''  # skip checksum — pinned for Kivy 2.3.0 / Cython 0.29 compatibility


recipe = HostPython3Recipe()
