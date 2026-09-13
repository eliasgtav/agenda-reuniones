@echo off
echo =========================================
echo  Compilando Agenda de Reuniones - Windows
echo  (c) Elias Gaytan Alvino
echo =========================================

pip install -r requirements.txt pyinstaller

REM La logica real de empaquetado vive en build_windows.py -- agrega a mano
REM los .dll de ANGLE/SDL2/GLEW y --collect-all kivymd, sin los cuales el
REM .exe compila pero se cae al abrir (ver comentario en ese archivo).
python build_windows.py

pause
