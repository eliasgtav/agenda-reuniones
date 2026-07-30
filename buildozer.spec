[app]
title = Agenda de Reuniones
package.name = agendareuniones
package.domain = com.eliasgt.agenda
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0

requirements = python3,kivy==2.3.1,kivymd==1.2.0,openpyxl,et_xmlfile,plyer,pillow,pyspellchecker,android,sqlite3,openssl

# Debe coincidir con la rama que se clona/parchea en build_apk.yml (p4a
# master sin pin, ver scripts/patch_p4a.py). Si no coincide, buildozer
# detecta "rama distinta" y borra + reclona p4a limpio, descartando los
# parches.
p4a.branch = master

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,RECORD_AUDIO,READ_CONTACTS,VIBRATE,RECEIVE_BOOT_COMPLETED,POST_NOTIFICATIONS,CAMERA
android.api = 34
android.minapi = 26
android.ndk = 25b
android.sdk = 35
android.accept_sdk_license = True
android.archs = arm64-v8a

# FileProvider para poder abrir archivos adjuntos (almacenamiento privado de
# la app) con otras apps (visor de PDF, imagenes, etc.) -- ver
# utils/abrir_archivo.py. Sin esto, Android bloquea compartir un file://
# de almacenamiento privado con FileUriExposedException.
# El <provider> del FileProvider NO se declara aqui (la opcion
# "android.extra_manifest_application_arguments" solo permite agregar
# ATRIBUTOS a la etiqueta <application>, no elementos hijos completos --
# ver scripts/patch_p4a.py, parche #3). Se inserta parcheando el template
# de p4a directamente.
android.enable_androidx = True
android.gradle_dependencies = androidx.core:core:1.12.0
android.add_resources = android_res

[buildozer]
log_level = 2
warn_on_root = 1
