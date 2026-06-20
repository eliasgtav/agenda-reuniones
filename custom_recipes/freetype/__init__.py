from pythonforandroid.recipes.freetype import FreetypeRecipe as _Base


class FreetypeRecipe(_Base):
    version = '2.12.1'
    sha512sum = ''  # skip checksum — version pinned for Kivy 2.3.0 compatibility


recipe = FreetypeRecipe()
