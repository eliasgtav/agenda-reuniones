"""
Parche HWUI: android:hardwareAccelerated="false" en PythonActivity
para evitar crash pthread_mutex_lock en Android 15 con SDL2.

Solo modifica el AndroidManifest — NO cambia la version de Python.
El commit 2ebea90d9d de p4a ya trae Python 3.11.5 con todos sus parches.
"""

import os

base = '.buildozer/android/platform/python-for-android/pythonforandroid/bootstraps'

candidates = [
    os.path.join(base, 'sdl2/build/templates/AndroidManifest.tmpl.xml'),
    os.path.join(base, '_sdl_common/build/templates/AndroidManifest.tmpl.xml'),
]

patched = False
for path in candidates:
    if os.path.exists(path):
        c = open(path).read()
        if 'android:hardwareAccelerated="false"' not in c:
            c = c.replace(
                'android:name="org.kivy.android.PythonActivity"',
                'android:name="org.kivy.android.PythonActivity"\n        android:hardwareAccelerated="false"',
                1,
            )
            open(path, 'w').write(c)
            print(f'HWUI fix aplicado: {path}')
        else:
            print(f'HWUI fix ya presente: {path}')
        patched = True
        break

if not patched:
    print('ADVERTENCIA: AndroidManifest template no encontrado')
    for p in candidates:
        print(f'  buscado: {p}  existe={os.path.exists(p)}')
