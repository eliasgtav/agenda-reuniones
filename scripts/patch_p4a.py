"""
Parche p4a para Android 15 (Honor MagicOS 9).

Usamos p4a commit 2ebea90d9d (julio 2025):
  - Python 3.11.5 con todos sus patches nativos correctos
  - SDL2 actualizado para NDK/Android reciente
No se necesita parchear versiones de Python.

Solo aplicamos el fix de HWUI: en Android 15, el renderizador HWUI de Honor
conflictúa con el OpenGL ES de SDL2 (crash: pthread_mutex_lock on destroyed
mutex en hwuiTask1). Solución: android:hardwareAccelerated="false" en Activity.
"""

manifest = '.buildozer/android/platform/python-for-android/pythonforandroid/bootstraps/_sdl_common/build/templates/AndroidManifest.tmpl.xml'

try:
    c = open(manifest).read()
    if 'android:hardwareAccelerated="false"' not in c:
        c = c.replace(
            'android:name="org.kivy.android.PythonActivity"',
            'android:name="org.kivy.android.PythonActivity"\n        android:hardwareAccelerated="false"',
            1
        )
        open(manifest, 'w').write(c)
        print('AndroidManifest: hardwareAccelerated=false aplicado (fix Android 15 Honor)')
    else:
        print('AndroidManifest: ya tiene hardwareAccelerated=false')
except Exception as e:
    print(f'AndroidManifest patch fallido: {e}')
