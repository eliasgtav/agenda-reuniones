# Manual de Usuario — Agenda de Reuniones de Trabajo

**Versión:** 1.0  
**Propiedad intelectual del diseño:** Elías Gaytan Alvino  
**Todos los derechos reservados © 2024**

---

## 1. Introducción

La **Agenda de Reuniones de Trabajo** es una aplicación móvil y de escritorio desarrollada
en Python con el framework Kivy/KivyMD. Permite gestionar reuniones de trabajo con alertas
de voz, registro de participantes, notas, conclusiones, adjuntos y exportación de datos.
Funciona completamente sin conexión a internet (modo offline-first con SQLite).

---

## 2. Requisitos del sistema

### Windows
- Windows 10 o superior
- Python 3.10+
- Dependencias: `pip install -r requirements.txt`
- Para TTS de voz: `pip install pyttsx3`

### Android
- Android 8.0 (API 26) o superior
- APK compilado con buildozer

---

## 3. Instalación y ejecución

### Modo desarrollo (Windows/macOS/Linux)
```bash
pip install -r requirements.txt
python main.py
```

### Ejecutable Windows
```bat
build_windows.bat
# Genera: dist\AgendaReuniones.exe
```

### APK Android
Requiere Linux o WSL con buildozer instalado:
```bash
chmod +x build_android.sh
./build_android.sh
# Genera: bin/agendareuniones-1.0-debug.apk
```

---

## 4. Pantallas y funciones

### 4.1 Dashboard (Inicio)

El panel principal muestra:
- **Tarjetas de resumen:** reuniones de hoy, pendientes, realizadas, canceladas,
  no asistidas y total general.
- **Lista de reuniones de hoy** con colores por estado.
- Botones de acceso rápido: Nueva Reunión y Ver Todas.

**Código de colores:**
| Estado       | Color        |
|--------------|--------------|
| Pendiente    | Amarillo     |
| Realizada    | Verde        |
| Cancelada    | Rojo         |
| No asistida  | Naranja      |

---

### 4.2 Nueva Reunión

Registro de una reunión con los siguientes campos:

| Campo        | Descripción                         |
|--------------|-------------------------------------|
| Asunto *     | Título de la reunión (obligatorio)  |
| Fecha        | Selector de calendario              |
| Hora         | Selector de hora                    |
| Lugar        | Texto libre                         |
| Participantes| Agregar/quitar asistentes           |
| Alertas      | 30 min / 1 hora / 1 día antes       |
| Notas        | Campo libre con soporte lápiz táctil|

Presiona **GUARDAR REUNIÓN** para registrar.

---

### 4.3 Lista de Reuniones

- **Búsqueda** por asunto o lugar en tiempo real.
- **Filtros por estado:** Todas / Pendientes / Realizadas / Canceladas / No asistidas.
- Por cada reunión: botones VER, EDITAR y BORRAR.
- **Exportar CSV** — guarda en la carpeta del usuario.
- **Exportar Excel** — con formato y colores por estado.

---

### 4.4 Detalle de Reunión

Acceso desde Lista → VER. Permite:

- Ver y editar **asunto, fecha, hora, lugar**.
- **Participantes:** marcar asistencia con checkbox, agregar o eliminar.
- **Notas:** área de texto amplia, compatible con lápiz táctil.
- **Conclusión:** área para el resumen de acuerdos.
- **Adjuntar archivos:** fotos, documentos, PDFs desde el dispositivo.
- **Grabar reunión:** inicia grabación de audio (requiere permiso de micrófono).
- **Cambiar estado:** Realizada / Cancelada / No asistí.
- **Terminar reunión:** guarda conclusión y marca como realizada.
- **Reprogramar:** cambiar fecha y hora desde el detalle.

---

## 5. Alertas y notificaciones

La app verifica cada minuto si una reunión está próxima y lanza:

1. **Notificación del sistema** (visual + sonido del dispositivo).
2. **Alerta de voz** que anuncia el asunto y la hora.

Ventanas de activación:
| Tipo de alerta | Se activa cuando faltan |
|----------------|-------------------------|
| 30 minutos     | Entre 25 y 35 minutos   |
| 1 hora         | Entre 55 y 65 minutos   |
| 1 día          | Entre 23:35 y 24:05 hrs |

Cada alerta se envía una sola vez (no se repite).

---

## 6. Exportación de datos

Los archivos se guardan en la carpeta de inicio del usuario (`~/`):

| Formato | Nombre de archivo                   |
|---------|-------------------------------------|
| CSV     | `agenda_reuniones_YYYYMMDD_HHMMSS.csv`  |
| Excel   | `agenda_reuniones_YYYYMMDD_HHMMSS.xlsx` |

El Excel incluye formato de celdas con colores por estado de reunión.

---

## 7. Modo oscuro

Actívalo con el ícono de luna (🌙) en la barra superior.
Alterna entre modo claro y oscuro en cualquier momento.

---

## 8. Base de datos

Los datos se almacenan localmente en SQLite:

- **Windows:** `C:\Users\<usuario>\agenda_reuniones.db`
- **Android:** directorio privado de la app

Tablas: `reuniones`, `participantes`, `archivos`, `alertas`.

---

## 9. Estructura del proyecto

```
agenda/
├── main.py                     # Punto de entrada
├── database.py                 # Capa de datos SQLite
├── requirements.txt            # Dependencias
├── buildozer.spec              # Configuración APK Android
├── build_windows.bat           # Script compilación Windows
├── build_android.sh            # Script compilación Android
├── screens/
│   ├── dashboard_screen.py     # Panel principal
│   ├── nueva_reunion_screen.py # Crear / editar reunión
│   ├── lista_reuniones_screen.py  # Lista con filtros y búsqueda
│   └── detalle_reunion_screen.py  # Detalle completo
└── utils/
    ├── notificaciones.py       # Alertas de voz y push
    └── exportar.py             # CSV y Excel
```

---

## 10. Propiedad intelectual

El diseño, arquitectura y código fuente de esta aplicación son propiedad intelectual de:

**Elías Gaytan Alvino**

Queda prohibida su reproducción, distribución o modificación sin autorización expresa
del autor.

© 2024 Elías Gaytan Alvino — Todos los derechos reservados.
