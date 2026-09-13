# Manual de Usuario — Agenda de Reuniones de Trabajo

**Versión:** 1.0
**Propiedad intelectual del diseño:** Elías Gaytan Alvino
**Todos los derechos reservados © 2024**

---

## 1. Introducción

La **Agenda de Reuniones de Trabajo** es una aplicación móvil (Android) y de escritorio
(Windows) desarrollada en Python con el framework Kivy/KivyMD. Permite gestionar reuniones
de trabajo de principio a fin: crearlas, capturar acuerdos y compromisos en vivo durante la
reunión, dar seguimiento a sus plazos, adjuntar archivos y grabaciones de audio, exportar la
información y enviar el acta por correo automáticamente.

Funciona **completamente sin conexión a internet** para todo lo relacionado con la agenda en
sí (reuniones, acuerdos, adjuntos, exportar, respaldo) — solo dos funciones puntuales
requieren internet: el envío del acta por correo y, en la versión de Windows, el dictado por
voz. Los datos se guardan localmente en una base de datos SQLite en el propio dispositivo.

---

## 2. Requisitos del sistema

### Android

- **Versión mínima:** Android 8.0 (API 26). Compilado y probado contra Android 14 (API 34).
- **Arquitectura:** el APK incluye solo la arquitectura de 64 bits (arm64-v8a) — no instala en
  dispositivos Android de 32 bits.
- **Permisos que solicita la app** (algunos se piden al usarlos por primera vez, no todos al
  instalar):
  - Internet (solo para enviar el acta por correo).
  - Almacenamiento (leer/escribir archivos adjuntos, exportaciones y respaldos).
  - Micrófono (dictado por voz y grabación de audio de la reunión).
  - Contactos (para elegir un participante directo de la libreta de contactos).
  - Cámara (para tomar la foto de perfil).
  - Estado del teléfono y registro de llamadas + enviar SMS (auto-respuesta a llamadas
    entrantes mientras se graba una reunión).
  - Acceso a la política de notificaciones "No Molestar" (para silenciar el timbre mientras
    se graba).
  - Notificaciones del sistema, vibración, e iniciar junto con el dispositivo.

### Windows (modo desarrollo actual / futuro ejecutable)

- Windows 10 o superior.
- Python 3.10 o superior (probado con 3.12).
- Dependencias exactas (ver `requirements.txt`):
  `kivy==2.3.1`, `kivymd==1.2.0`, `openpyxl==3.1.2`, `plyer==2.1.0`, `pillow==10.3.0`,
  `pyspellchecker`, `pyttsx3`, `SpeechRecognition`, `PyAudio`.
- El **dictado por voz en Windows requiere conexión a internet** (usa el servicio de
  reconocimiento de Google a través de la librería `SpeechRecognition`) y un micrófono
  reconocido por el sistema.

### General

- Base de datos SQLite local — en Windows vive en `C:\Users\<usuario>\agenda_reuniones.db`;
  en Android, en el almacenamiento privado de la app.
- La configuración/perfil del usuario se guarda en `agenda_config.json`, en la misma carpeta
  que la base de datos. La contraseña de correo se guarda **cifrada**, nunca en texto plano.

---

## 3. Instalación y ejecución

### Modo desarrollo (Windows/macOS/Linux)

```bash
pip install -r requirements.txt
python main.py
```

### Ejecutable Windows (.exe)

```bat
build_windows.bat
:: Genera: dist\AgendaReuniones.exe (PyInstaller, un solo archivo)
```

### APK Android

El APK se compila automáticamente en **GitHub Actions** (`.github/workflows/build_apk.yml`)
cada vez que se sube un cambio al repositorio — no hace falta configurar nada localmente. El
archivo `.apk` queda disponible como "artifact" descargable en la ejecución (run) correspondiente,
en la pestaña *Actions* del repositorio.

Alternativamente, para compilar en un entorno Linux/WSL propio con `buildozer` instalado:

```bash
chmod +x build_android.sh
./build_android.sh
# Genera: bin/agendareuniones-1.0-debug.apk
```

Para instalar el APK en un celular conectado por USB (con depuración USB activada):

```bash
adb install -r AgendaReuniones.apk
```

---

## 4. Pantallas y funciones

### 4.1 Ingreso (solo la primera vez)

La primera vez que se abre la app, antes de llegar al Dashboard, pide registrar:

- **Nombres \*** y **Apellidos \*** (obligatorios, se escriben en mayúsculas automáticamente).
  Un círculo muestra las iniciales en vivo mientras se escribe.

Botón **INGRESAR A LA APP**: valida que ambos campos estén llenos y guarda el perfil. Esta
pantalla no vuelve a aparecer en usos posteriores (a menos que se borre la configuración).

---

### 4.2 Dashboard (Inicio)

Pantalla principal a la que se llega después de iniciar la app.

- **Tarjeta de perfil** (arriba, tocable): foto o iniciales del usuario, nombre completo, y
  "Toca para editar perfil" → lleva a Mi Perfil.
- **"Resumen General"**: 6 tarjetas de estadística, cada una tocable — al tocarla, abre Lista
  de Reuniones ya filtrada por ese estado:

  | Tarjeta      | Color     |
  |--------------|-----------|
  | Hoy          | Azul      |
  | Pendientes   | Amarillo  |
  | Realizadas   | Verde     |
  | Canceladas   | Rojo      |
  | No asistidas | Naranja   |
  | Total        | Morado    |

- Botón **VER TODAS LAS REUNIONES** → Lista de Reuniones (sin filtro).
- Botón **SEGUIMIENTO DE ACUERDOS** (muestra un contador entre paréntesis si hay acuerdos
  activos, p. ej. "SEGUIMIENTO DE ACUERDOS (3)") → pantalla de Seguimiento.

---

### 4.3 Nueva Reunión

Formulario para registrar una reunión:

| Campo          | Descripción                                                      |
|----------------|-------------------------------------------------------------------|
| Asunto \*      | Título de la reunión (obligatorio, mayúsculas automáticas)       |
| Fecha \*       | Selector de calendario (se muestra DD/MM/AAAA)                   |
| Hora           | Selector de reloj (si se deja vacía, se usa 09:00 por defecto)   |
| Lugar          | Texto libre, con dictado por voz                                 |
| Modalidad      | PRESENCIAL o VIRTUAL (dos botones exclusivos)                    |
| Participantes  | Agregar/quitar asistentes (a mano o por voz), sin duplicados     |
| Alertas        | 3 interruptores: 10 min / 15 min / 30 min antes (activos por defecto) |

Botones **CANCELAR** (vuelve sin guardar) y **GUARDAR REUNIÓN** (valida asunto y fecha; si
falta algo, muestra el aviso correspondiente; si guarda con éxito, muestra "Reunión guardada"
y regresa al Dashboard).

---

### 4.4 Lista de Reuniones

- **Búsqueda** en tiempo real por asunto o lugar, con corrector ortográfico integrado.
- **Filtros por estado** (botones de color): Todas, Hoy, Pendientes, Realizadas, Canceladas,
  No asistidas.
- **Exportar a Excel**: genera un archivo `.xlsx` con colores de fondo por estado, guardado en
  la carpeta de Descargas del dispositivo; al terminar, ofrece abrirlo directamente.
- **Scroll infinito**: la lista trae 40 reuniones a la vez y carga más automáticamente al
  llegar cerca del final — pensado para no perder velocidad aunque haya cientos o miles de
  reuniones guardadas.
- Cada tarjeta de reunión muestra asunto, estado, fecha (en español) + hora + lugar, y los
  botones **VER** (abre el Detalle) y **BORRAR** (pide confirmación antes de eliminar).

---

### 4.5 Detalle de Reunión

La pantalla más completa de la app. Se llega desde Lista → VER, o desde Seguimiento → "VER
REUNIÓN" de un acuerdo puntual.

**Encabezado**: asunto, fecha + hora + lugar, y una línea de estado que cambia según el caso:
- Si ya pasó la hora y la reunión sigue "pendiente": el botón **EN REUNIÓN** se activa (rojo)
  y el texto dice "EN REUNIÓN — ¡Es hora!".
- Si aún no llega la hora: muestra una cuenta regresiva ("EN REUNIÓN se activa en N min").
- Si el estado ya es realizada/cancelada/no asistida: solo muestra ese estado, sin cuenta
  regresiva. El color de fondo del encabezado cambia según el estado (amarillo/verde/rojo/
  naranja).

**Botones de estado**: **REALIZADA**, **CANCELADA**, **NO ASISTÍ**, y **EN REUNIÓN** (lleva a
la pantalla en vivo de captura de acuerdos, solo se activa cuando ya llegó la hora y la
reunión sigue pendiente).

**Participantes**: lista con casilla "Asistió" (se guarda al tocarla) y botón para eliminar;
abajo, un campo para agregar uno nuevo a mano, por voz, o eligiéndolo directo de los contactos
del teléfono (solo Android).

**Desarrollo de la Reunión** y **Objetivos de la Reunión**: dos campos de texto amplios
(compatibles con lápiz táctil y dictado por voz) para las notas generales.

**Acuerdos y Compromisos**: campo de texto que numera automáticamente cada línea nueva
("1.- ", "2.- ", …) al presionar Enter — pensado para llevar una lista simple de acuerdos en
texto libre.

**Acciones, responsables y plazos de cumplimiento** (tabla de "acuerdos con plazo",
independiente del campo anterior): cada acuerdo se registra en un diálogo aparte con:
- Descripción (multilínea; puede "traer" una línea ya escrita en el campo de Acuerdos y
  Compromisos de arriba para no reescribirla),
- Responsable (a mano, por voz, o eligiéndolo de un menú si ya hay participantes
  registrados),
- Prioridad: **Baja**, **Media** (por defecto) o **Alta**, con un semáforo de colores,
- Plazo (fecha, obligatoria) y hora del plazo (opcional).

Cada tarjeta de acuerdo muestra su prioridad, título, el responsable (con avatar de inicial),
la fecha límite, y un estado: **PENDIENTE**, **COMPLETADO**, o **VENCIDO** (calculado
automáticamente si el plazo ya pasó sin completarse). Un checkbox marca completado/pendiente
directamente desde la tarjeta.

**Archivos adjuntos**: lista de documentos, fotos o grabaciones de audio (con botón
reproducir/detener) adjuntos a la reunión, cada uno con botón para eliminarlo. Botón
**ADJUNTAR ARCHIVO** abre el selector nativo del sistema.

**Grabar Reunión**: pide permiso de micrófono la primera vez. Al iniciar la grabación,
además intenta (sin bloquear la grabación si algo de esto falla):
- Activar la auto-respuesta por SMS a llamadas entrantes, si hay un mensaje configurado en Mi
  Perfil (avisa si el usuario niega el permiso necesario).
- Silenciar el timbre del teléfono mientras dura la grabación (pide, si hace falta, el
  permiso especial "Acceso a No Molestar", explicando por qué).

Al detener la grabación, el audio queda adjunto a la reunión y se restauran el timbre normal
y la auto-respuesta.

**Guardar Cambios**: guarda desarrollo/notas/conclusión sin cambiar el estado de la reunión.

**Terminar Reunión**: guarda todo y marca la reunión como "realizada". Si hay una cuenta de
correo configurada en Mi Perfil, **envía automáticamente el acta de la reunión** al correo
destinatario configurado (ver sección 8).

**Reprogramar reunión**: permite elegir una nueva fecha y/o una nueva hora (se puede cambiar
solo una de las dos) y confirmar el cambio.

---

### 4.6 En Reunión (captura en vivo)

Se llega únicamente desde el botón **EN REUNIÓN** de Detalle, una vez que ya es la hora de la
reunión. Pensada para anotar acuerdos rápido, sobre la marcha, mientras la reunión ocurre:

- Campo de texto (con corrector ortográfico y dictado por voz) para el acuerdo.
- Responsable (opcional) y Plazo de cumplimiento (opcional, selector de calendario).
- Botón **+ AGREGAR ACUERDO**: agrega el acuerdo (con hora, texto, responsable y plazo) a una
  lista visible en pantalla, cada uno con su propia "x" para borrarlo.
- **GUARDAR EN NOTAS**: vuelca todo lo capturado al bloque de notas de la reunión (y a la
  tabla de acuerdos con plazo, si tienen plazo), sin duplicar lo que ya se hubiera guardado
  antes.
- **Autoguardado silencioso**: si se sale de esta pantalla sin tocar "GUARDAR EN NOTAS" (por
  ejemplo por una llamada entrante), lo capturado se guarda automáticamente igual, para no
  perder nada.

---

### 4.7 Seguimiento de Acuerdos

Vista global de **todos** los acuerdos con plazo de **todas** las reuniones (a diferencia de
la tabla de acuerdos de Detalle, que muestra solo los de una reunión puntual):

- Scroll infinito (40 acuerdos a la vez).
- Cada tarjeta indica también a qué reunión pertenece, con un botón **VER REUNIÓN** que lleva
  directo a su Detalle.
- El checkbox de completado/pendiente actualiza solo esa tarjeta, sin recargar toda la lista
  ni perder la posición del scroll.

---

### 4.8 Mi Perfil

- **Foto de perfil**: al tocar el círculo, permite elegir **GALERÍA**, **CÁMARA** (solo
  Android) o **QUITAR FOTO**. Al elegir una imagen, se abre un recortador circular
  (arrastrar/pellizcar) antes de guardarla.
- **Nombres \* / Apellidos \***, con botones **CAMBIAR FOTO** y **GUARDAR PERFIL**.
- **Configuración de correo** (para el envío automático del acta al terminar una reunión):
  correo remitente, contraseña de aplicación (campo oculto), correo destinatario, y servidor
  SMTP (por defecto `smtp.gmail.com`). Para Gmail hace falta activar la verificación en 2
  pasos y generar una "Contraseña de aplicación" específica. Botones **GUARDAR CORREO** y
  **PROBAR ENVÍO** (manda un correo de prueba real y avisa si hubo éxito o el motivo del
  error). La contraseña se guarda cifrada en disco.
- **Auto-respuesta de llamadas al grabar**: mensaje de texto que se envía por SMS
  automáticamente a quien llame mientras se está grabando una reunión.
- **Copia de seguridad**:
  - **HACER BACKUP**: copia toda la base de datos a un archivo en Descargas
    (`agenda_backup_<fecha_hora>.db`), en segundo plano.
  - **IMPORTAR BACKUP**: elige un archivo `.db` (verifica que sea un backup válido de esta
    app), pide confirmación explícita — reemplaza **todas** las reuniones actuales, es
    irreversible, y pide cerrar y volver a abrir la app después de importar.
- **Eliminar todas las reuniones**: con doble confirmación, borra permanentemente todas las
  reuniones, participantes, alertas y acuerdos, además de los archivos adjuntos y grabaciones
  físicas asociadas.

---

## 5. Alertas y notificaciones

La app revisa automáticamente cada 60 segundos (mientras está abierta) si hay algo que avisar.

**Alertas de reunión próxima** (según los interruptores activados en Nueva Reunión — la
revisión es periódica, no un temporizador exacto, por eso cada una tiene un pequeño margen):

| Alerta configurada | Se dispara si faltan entre |
|---------------------|------------------------------|
| 10 minutos antes    | 5 y 15 minutos                |
| 15 minutos antes    | 10 y 20 minutos                |
| 30 minutos antes    | 25 y 35 minutos                |

Cada alerta se envía **una sola vez** por reunión.

**Alertas de plazo de un acuerdo** (aplica a cualquier acuerdo con plazo, de cualquier
reunión): avisa hasta 3 veces conforme se acerca la fecha — "vence mañana" → "vence hoy" →
"vencido" — sin repetir nunca la misma categoría dos veces.

Cada alerta llega de dos formas al mismo tiempo:
1. **Notificación del sistema** (visual, con una duración de 15 segundos).
2. **Alerta hablada**, en español, mencionando el nombre del usuario y el motivo del aviso.

---

## 6. Funciones disponibles en varias pantallas

- **Dictado por voz**: disponible en la mayoría de los campos de texto (ícono de micrófono).
  En Android usa el reconocimiento de voz nativo del sistema. **En Windows requiere conexión
  a internet** y un micrófono reconocido por el sistema operativo.
- **Corrector ortográfico**: en los campos de búsqueda y de captura en vivo, sugiere
  correcciones — funciona completamente offline.
- **Modo oscuro**: ícono de luna (🌙) en la barra inferior, alterna entre claro y oscuro en
  cualquier momento, aplica a toda la app.
- **Elegir contacto** (Android, en Detalle de Reunión): toma un nombre directo de la libreta
  de contactos del teléfono como participante.

---

## 7. Base de datos

Los datos se almacenan localmente en SQLite:

- **Windows:** `C:\Users\<usuario>\agenda_reuniones.db`
- **Android:** almacenamiento privado de la app

Tablas principales: `reuniones`, `participantes`, `archivos`, `alertas`, `acuerdos`.

---

## 8. Estructura del proyecto

```
agenda/
├── main.py                         # Punto de entrada
├── database.py                     # Capa de datos SQLite
├── requirements.txt                # Dependencias (modo desarrollo/Windows)
├── buildozer.spec                  # Configuración del APK Android
├── build_windows.bat               # Compila el .exe de Windows (PyInstaller)
├── build_android.sh                # Compila el APK localmente (Linux/WSL + buildozer)
├── .github/workflows/build_apk.yml # Compila el APK automáticamente en GitHub Actions
├── screens/
│   ├── login_screen.py             # Ingreso (solo primera vez)
│   ├── dashboard_screen.py         # Panel principal
│   ├── nueva_reunion_screen.py     # Crear reunión
│   ├── lista_reuniones_screen.py   # Lista con filtros, búsqueda y exportar
│   ├── detalle_reunion_screen.py   # Detalle completo de una reunión
│   ├── en_reunion_screen.py        # Captura de acuerdos en vivo
│   ├── seguimiento_screen.py       # Seguimiento global de acuerdos con plazo
│   └── perfil_screen.py            # Perfil, correo, backup
└── utils/
    ├── notificaciones.py           # Alertas de voz y del sistema
    ├── exportar.py                 # Exportar a Excel/CSV y hacer backup
    ├── email_sender.py             # Envío del acta por correo
    ├── llamadas.py                 # Auto-respuesta SMS a llamadas entrantes
    ├── silenciador.py              # Silenciar el timbre al grabar
    ├── voz.py                      # Dictado por voz
    └── config.py                   # Perfil y configuración del usuario
```

---

## 9. Propiedad intelectual

El diseño, arquitectura y código fuente de esta aplicación son propiedad intelectual de:

**Elías Gaytan Alvino**

Queda prohibida su reproducción, distribución o modificación sin autorización expresa
del autor.

© 2024 Elías Gaytan Alvino — Todos los derechos reservados.
