# CLAUDE.md

Contexto para Claude Code al trabajar en este repositorio.

## Qué es esto

**Agenda de Reuniones de Trabajo** — app Python/Kivy/KivyMD, offline-first (SQLite local),
para Windows y Android. Propiedad intelectual de Elías Gaytan Alvino. Ver `manual.md` para
el manual de usuario.

- Ejecutar en desarrollo: `py -3.12 main.py`
- `database.py` — SQLite en `~/agenda_reuniones.db` (Windows) / almacenamiento privado de la
  app (Android)
- `utils/config.py` — config JSON en `~/agenda_config.json`
- `screens/` — 8 pantallas (dashboard, nueva_reunion, lista_reuniones, detalle_reunion,
  perfil, login, en_reunion, seguimiento)
- `buildozer.spec` + `.github/workflows/build_apk.yml` — build de APK en GitHub Actions
- `scripts/` — herramientas de desarrollo (no se compilan al APK): parches de p4a,
  benchmarks, generación de datos de prueba
- `java_src/` — código Java propio que se compila al APK (`android.add_src`): alarmas de
  AlarmManager para las alertas con la app cerrada

## Sesión 2026-08-22 — revisión de seguridad y rendimiento con volumen de datos

El usuario pidió revisar 6 puntos antes de considerar la app "versión final": backend,
protección de roles, datos sensibles, seguridad de passwords, prueba de carga, filtros de
validación. Commits `3677781` y `a46b93b`.

### Fixes de seguridad aplicados (commit `3677781`)
- **`utils/config.py`**: la contraseña de correo (App Password de Gmail) ya no se guarda en
  texto plano — cifrado XOR+base64 con clave SHA-256 fija (`_cifrar_password`/
  `_descifrar_password`), campo en disco `correo_password_enc`. Instalaciones viejas con
  `correo_password` en claro se migran solas la próxima vez que `guardar()` corre.
- **`utils/archivo_selector.py`**: el nombre de archivo adjunto que devuelve el
  `ContentResolver` de Android se sanea con `os.path.basename()` antes de guardarlo (evita
  path traversal si un proveedor de contenido devuelve algo tipo `../../otro_archivo`).
- **`utils/exportar.py`**: texto de usuario que empiece con `=`, `+`, `-` o `@` se antepone
  con `'` antes de escribirlo en CSV/Excel (`_valor_seguro`) — evita inyección de fórmulas
  al abrir el archivo exportado en Excel.
- **`utils/llamadas.py`**: el log de depuración que escribía cada número de teléfono
  entrante a disco (`llamadas_debug.log`) quedó apagado por defecto (`_DEBUG_LLAMADAS =
  False`).

### No son huecos "por arreglar" — son la arquitectura actual de la app
- No hay backend/servidor: todo local (Kivy + SQLite), sin superficie de ataque remota.
  Las queries SQL usan parámetros `?` en todos lados, sin inyección SQL practicable.
- No hay roles ni autenticación real — el "login" solo pide nombre para personalizar
  alertas de voz. Mono-usuario por diseño, no un bug.
- No aplica "usuarios concurrentes": no hay servidor, cada instalación corre sola.

### Rendimiento con volumen: índices + paginación (commit `a46b93b`)
`scripts/benchmark_carga.py` (puebla una BD SQLite **temporal** aparte, nunca la real) mostró
que sin índices, con 10000 reuniones, `listar_reuniones()` sin filtro tardaba ~290ms y
`stats_dashboard()` ~158ms — cada `WHERE estado=?`/`fecha=?` hacía recorrido completo de
tabla, y las pantallas de lista cargaban todo el resultado de una vez sin paginar.

- **`database.py`**: 8 índices nuevos (`CREATE INDEX IF NOT EXISTS`, se aplican solos
  también en instalaciones existentes) sobre `reuniones(fecha)`, `reuniones(estado)`,
  `participantes(reunion_id)`, `archivos(reunion_id)`, `alertas(reunion_id)`,
  `acuerdos(reunion_id)`, `acuerdos(estado)`, `acuerdos(plazo)`. `listar_reuniones()` y
  `listar_todos_acuerdos()` ganaron parámetros opcionales `limit`/`offset` (default `None`,
  no rompe a quien no los pase — Exportar a Excel sigue trayendo el set completo).
- **`screens/lista_reuniones_screen.py`** y **`screens/seguimiento_screen.py`**: scroll
  infinito (`PAGE_SIZE = 40`), carga la siguiente página al acercarse al final del
  `MDScrollView` (`on_scroll_y`, dispara `cargar_mas()` con `scroll_y <= 0.15`).
- Resultado medido (10000 reuniones): `stats_dashboard()` 158ms→3ms, filtro "Hoy" 28ms→
  1.6ms, primera página real de Lista de Reuniones 290ms→2.6ms. Las búsquedas de texto
  (`LIKE %...%`) no mejoran con índices normales (limitación de fondo de SQLite, haría falta
  FTS5), pero con `limit=40` el usuario ya no lo nota.
- Confirmado en pantalla real por el usuario: el scroll se siente rápido en ambas pantallas.

### Herramientas de desarrollo nuevas en `scripts/`
- **`benchmark_carga.py`**: mide tiempos de consulta contra una BD SQLite temporal (nunca la
  real), en escalas de 100 a 10000 reuniones.
- **`insertar_datos_prueba.py`**: inserta reuniones/acuerdos de prueba en la BD **real**
  (marcados con prefijo `[PRUEBA] `), `--limpiar` los borra sin tocar datos reales. Los
  acuerdos de prueba usan plazo siempre futuro (5-180 días) a propósito — un plazo
  vencido/hoy dispara de verdad las alertas de voz de `utils/notificaciones.py` cada 60s
  (`main.py::_check_alertas`) y satura de avisos al abrir la app.
- **`benchmark_carga_real.py`**: como `benchmark_carga.py` pero inserta en bloque y mide
  directo sobre la BD real (comparte el `--limpiar` con `insertar_datos_prueba.py`, mismo
  prefijo). Nota técnica: no asumir que el próximo id es `MAX(id)+1` — con `AUTOINCREMENT`,
  el contador de SQLite no retrocede aunque se borren filas; usar
  `SELECT last_insert_rowid()` después de un `executemany()` en vez de calcular el id antes.

### Notas de entorno (para la próxima sesión)
- `Database._conn()` no cierra sus conexiones explícitamente (solo hace commit al salir del
  `with`) — en Windows puede dejar el archivo `.db` bloqueado un momento; cualquier script
  que borre un archivo `.db` temporal debe envolver el `os.remove()` en `try/except
  PermissionError`.
- Lanzar la app con Bash (`py -3.12 main.py &`, incluso con `disown`) **no** deja la ventana
  abierta más allá de la llamada a la herramienta. Lo que sí funciona para dejarla visible en
  la pantalla del usuario: PowerShell `Start-Process -FilePath "py" -ArgumentList
  "-3.12","main.py" -WorkingDirectory "<ruta>" -WindowStyle Normal`.

## Sesión 2026-10-24 — alertas: márgenes exactos y aviso con la app cerrada

Commits `4392907`, `92958bd`, `452282e`. Todo confirmado por el usuario en el celular real
(HONOR Magic6 Lite, Android 15).

### Nombres y márgenes de las alertas de reunión (commit `4392907`)
- Los tipos internos de alerta se llamaban `'30min'`/`'1hora'`/`'1dia'` aunque la pantalla
  siempre dijo "10/15/30 min antes" (fuente de confusión real en esta sesión). Ahora son
  `'10min'`/`'15min'`/`'30min'` en `screens/nueva_reunion_screen.py` (ids `sw_10min`/
  `sw_15min`/`sw_30min`), `utils/notificaciones.py` y `scripts/benchmark_carga.py`.
- **Migración de BD**: `database.py::_init_db` renombra los tipos viejos con un solo `UPDATE
  ... CASE` gateado por `PRAGMA user_version < 1` (luego lo fija en 1). No quitar el gate ni
  partirlo en tres UPDATE: `'1dia'→'30min'` chocaría con el `'30min'` viejo, y correrlo dos
  veces convertiría los `'30min'` nuevos en `'10min'`. Un backup viejo importado
  (user_version 0) se migra solo al reabrir la app. Primera vez que el proyecto usa
  `user_version`: futuras migraciones de datos (no de columnas) deberían seguir ese patrón.
- `UMBRALES` ahora es `(lo, hi]` con `hi` = el tiempo de la pantalla: `10min (5,10]`,
  `15min (10,15]`, `30min (25,30]`. Antes era `hi±5`, y con la app abierta cada alerta
  sonaba ~5 min antes de lo que decía (el chequeo de 60s la tomaba al entrar a la ventana).

### Alertas con la app cerrada (commit `92958bd`)
Antes las alertas solo sonaban con la app en pantalla: no hay servicio, y en Android el
Clock de Kivy (con `main.py::_check_alertas`) se pausa en segundo plano. El usuario eligió
AlarmManager + notificación nativa en vez de un foreground service (batería, y Magic OS
mata esos servicios).
- **`java_src/com/eliasgt/agenda/alarmas/AlarmasAgenda.java`**: `reemplazarTodas(ctx,
  json)` cancela y reprograma todo (exacta con `setExactAndAllowWhileIdle` si
  `canScheduleExactAlarms()`, si no inexacta); guarda las alarmas en SharedPreferences
  `agenda_alarmas` para reprogramarlas sin Python. Al sonar muestra la notificación (canal
  `agenda_alertas`, IMPORTANCE_HIGH, tocarla abre la app) y la anota en "disparadas";
  `consumirDisparadas()` las devuelve a Python.
- **`AlarmaReceiver.java`**: recibe las alarmas y `BOOT_COMPLETED`/`MY_PACKAGE_REPLACED`
  (reiniciar o actualizar la app borra todas las alarmas de AlarmManager). Declarado en el
  manifest por `scripts/patch_p4a.py` **parche #6** (mismo motivo que el #4: `<receiver>` es
  hijo de `<application>`, no sirve `extra_manifest_*`).
- **`utils/alarmas.py`**: puente jnius, no-op fuera de Android. Máx. 60 alarmas (las más
  próximas) — AlarmManager lanza excepción pasadas 500 por app. Solo llama a Java si la
  lista cambió.
- **`NotificacionesManager`** (`utils/notificaciones.py`): cada tick primero
  `_procesar_disparadas()` (marca enviada lo que ya avisó Android y dice la voz si sonó hace
  < 10 min — así "tocar la notificación" dice la alerta), luego el chequeo normal, y al
  final `programar_alarmas()` (lo recién avisado sale de la lista y su alarma se cancela;
  recoge reuniones nuevas/editadas/borradas en ≤60s). Sin avisos dobles en ningún orden.
  Claves: `r{alerta_id}` (request code par) y `c{acuerdo_id}:{categoria}` (impar).
- Acuerdos: alarmas a las 09:00 (`HORA_AVISO_ACUERDO`) del día antes / del día / del día
  después del plazo; `acuerdos_con_plazo_pendientes(solo_proximos=False)` trae también los de
  plazo lejano.
- `main.py`: `on_pause` fuerza `programar_alarmas()`; `on_resume` corre `_check_alertas` al
  instante en vez de esperar el siguiente tick.
- `buildozer.spec`: `android.add_src = java_src`, permisos `USE_EXACT_ALARM`,
  `SCHEDULE_EXACT_ALARM`.
- **Bug encontrado de paso**: `POST_NOTIFICATIONS` estaba en el manifest pero nunca se pedía
  en tiempo de ejecución — con targetSdk 34, en Android 13+ las notificaciones quedan
  bloqueadas hasta que se acepta (deducido de la regla de Android, no comprobado antes del
  fix si las de plyer salían o no). Ahora
  `utils/alarmas.py::pedir_permiso_notificaciones()` en `on_start`.
- Si en algún teléfono no llegan con la app cerrada: primero el ahorro de batería del
  fabricante (HONOR: Ajustes → Batería → Inicio de aplicaciones → gestión manual), luego
  `adb shell dumpsys alarm | grep agendareuniones` para ver si las alarmas existen.
- El código Java no se puede compilar en Windows (no hay SDK local): solo se valida en el
  build de GitHub Actions. Para verificar el APK sin instalarlo: `classes*.dex` debe
  contener `AlarmasAgenda` y el `AndroidManifest.xml` binario (strings UTF-16) `AlarmaReceiver`.

### Notas de entorno
- `git push` (Bash o PowerShell) imprime `gh.exe auth git-credential store: ... command not
  found` — inofensivo, el push sí se hace. `gh` está en
  `C:\Users\GABLAS\AppData\Local\gh-cli\bin\gh.exe` (no en el PATH); el build tarda
  ~10-15 min (`gh run watch <id> --exit-status`), el APK sale del artifact
  `AgendaReuniones-APK` (`gh run download <id> -n AgendaReuniones-APK -D <dir>`).
- `adb` no está instalado; bajar platform-tools requiere que el usuario lo autorice.
