from pythonforandroid.recipes.python3 import Python3Recipe as _Base


class Python3Recipe(_Base):
    version = '3.12.9'
    sha512sum = ''  # skip checksum
    patches = []    # base patches are version-specific y no se aplican a 3.12.9


recipe = Python3Recipe()
