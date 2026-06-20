@echo off
echo =========================================
echo  Compilando Agenda de Reuniones - Windows
echo  (c) Elias Gaytan Alvino
echo =========================================

pip install pyinstaller kivymd kivy openpyxl plyer pillow pyttsx3

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "AgendaReuniones" ^
    --add-data "screens;screens" ^
    --add-data "utils;utils" ^
    --hidden-import kivymd ^
    --hidden-import plyer ^
    --hidden-import openpyxl ^
    --hidden-import pyttsx3 ^
    main.py

echo.
echo Ejecutable generado en: dist\AgendaReuniones.exe
pause
