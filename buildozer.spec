[app]
title = Agenda de Reuniones
package.name = agendareuniones
package.domain = com.eliasgt.agenda
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db
version = 1.0

requirements = python3,kivy==2.3.0,kivymd==1.2.0,openpyxl,plyer,pillow,android

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,RECORD_AUDIO,VIBRATE,RECEIVE_BOOT_COMPLETED
android.api = 33
android.minapi = 26
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True
android.arch = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
