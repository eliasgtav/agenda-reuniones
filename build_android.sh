#!/bin/bash
# Script de compilación Android
# © Elías Gaytan Alvino

echo "=== Instalando buildozer ==="
pip install buildozer cython

echo "=== Compilando APK para Android ==="
buildozer -v android debug

echo "=== APK generado en: bin/ ==="
ls -lh bin/*.apk 2>/dev/null || echo "Revisa errores arriba."
