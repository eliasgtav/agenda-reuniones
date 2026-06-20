from pythonforandroid.recipes.hostpython3 import HostPython3Recipe as _Base


class HostPython3Recipe(_Base):
    version = '3.12.9'
    sha512sum = ''  # skip checksum
    patches = []    # base patches are version-specific and no se aplican a 3.12.9


recipe = HostPython3Recipe()
