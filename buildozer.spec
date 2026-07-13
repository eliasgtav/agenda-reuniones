[app]
title = Agenda de Reuniones
package.name = agendareuniones
package.domain = com.eliasgt.agenda
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0

requirements = python3,kivy==2.3.1,kivymd==1.2.0,openpyxl,plyer,pillow,android,sqlite3,openssl

# Debe coincidir con la rama que se clona/parchea en build_apk.yml (p4a
# master sin pin, ver scripts/patch_p4a.py). Si no coincide, buildozer
# detecta "rama distinta" y borra + reclona p4a limpio, descartando los
# parches.
p4a.branch = master

orientation = portrait
fullscreen = 1

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,RECORD_AUDIO,VIBRATE,RECEIVE_BOOT_COMPLETED,POST_NOTIFICATIONS
android.api = 35
android.minapi = 26
android.ndk = 25b
android.sdk = 35
android.accept_sdk_license = True
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
