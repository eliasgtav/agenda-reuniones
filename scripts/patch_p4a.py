"""
Parches para compilar con p4a master (Python 3.14 con sus parches oficiales)
+ Kivy 2.3.1:

Por que p4a master y no un commit pineado:
- Se probo pinear p4a a un commit viejo (2ebea90d9d, jul-2025) para evitar
  Python 3.14, buscando el ultimo commit con Python 3.11.5 nativo. Eso
  rompio la compilacion de CUALQUIER paquete con pyproject.toml (pyjnius
  incluido, obligatorio en toda app Kivy): ese commit usaba
  "python -m build --wheel" con entorno aislado, mecanismo que fallaba con
  "pyproject_hooks.BackendUnavailable: Cannot import 'setuptools.build_meta'".
  Ese bug se arreglo en p4a recien en mar-2026 (soporte de wheels
  precompilados), pero ya con Python 3.14 como version por defecto - no hay
  un commit que tenga ambas cosas (Python 3.11 nativo + el fix).
- Verificado en el repo real de p4a (jun-2026): el recipe oficial de Kivy
  en master ya esta fijado en 2.3.1 (misma version que usamos), combinado
  con Python 3.14 y sus parches oficiales completos - a diferencia del
  intento anterior de forzar 3.12.9 a mano, que se saltaba esos parches y
  producia fallos de enlazado en tiempo de ejecucion (p.ej. "cannot locate
  symbol PyExc_ValueError" al importar math).

Parches aplicados aqui (siguen siendo necesarios en p4a master, confirmado
contra el codigo actual del recipe python3):
1. recipes/python3: stdlib.zip con ZIP_STORED (zip -X -0, sin compresion)
   para que zipimport no necesite zlib al inicio - sin esto Python no
   puede importar encodings durante la inicializacion (HAVE_ZLIB_H no
   definido en cross-compile). Confirmado en dispositivo real: sin este
   fix, 553/553 entradas de stdlib.zip quedan en DEFLATE y el arranque
   de Python falla con "failed to get the Python codec of the filesystem
   encoding".
2. start.c: diagnostico en archivo (~/files/startc_diag.txt, legible con
   `adb shell run-as <paquete> cat files/startc_diag.txt` incluso si la
   app crashea) + fix de la condicion de carrera donde ANDROID_ARGUMENT
   puede llegar NULL de Java antes que SDL lo setee.
"""

import os
import glob

base = '.buildozer/android/platform/python-for-android/pythonforandroid/recipes'

# --- 1. recipes/python3: forzar ZIP_STORED en stdlib.zip ---
# zipimport en C necesita HAVE_ZLIB_H para descomprimir DEFLATE. Si no esta
# definido al compilar (cross-compile con NDK), Python no puede leer NINGUNA
# entrada de stdlib.zip -> falla al importar encodings al init.
#
# stdlib.zip NO se crea con el modulo zipfile de Python sino invocando el
# binario `zip -X` en create_python_bundle() del recipe python3. `zip`
# comprime con DEFLATE por defecto salvo que se le pase `-0` (store).
python3_recipe_path = f'{base}/python3/__init__.py'
if os.path.exists(python3_recipe_path):
    c = open(python3_recipe_path).read()
    pat = "shprint(sh.zip, '-X', stdlib_zip, *stdlib_filens)"
    if pat in c:
        c = c.replace(pat, "shprint(sh.zip, '-X', '-0', stdlib_zip, *stdlib_filens)")
        open(python3_recipe_path, 'w').write(c)
        print('recipes/python3/__init__.py parcheado: zip -X -0 (STORED) para stdlib.zip')
    elif "'-0'" in c and 'stdlib_zip' in c:
        print('recipes/python3/__init__.py: ya tiene -0 (STORED)')
    else:
        print('WARN: patron de zip stdlib_zip no encontrado en recipes/python3/__init__.py '
              '(revisar si create_python_bundle cambio)')
else:
    print('WARN: recipes/python3/__init__.py no encontrado')

# --- 2. start.c: diagnostico en archivo + fix race condition ANDROID_ARGUMENT ---
start_c_paths = glob.glob('.buildozer/**/start.c', recursive=True)

if start_c_paths:
    start_c_path = start_c_paths[0]
    print(f'Parcheando start.c: {start_c_path}')
    src = open(start_c_path).read()

    DIAG_FUNC = r"""
/* === DIAGNOSTICO ARCHIVO: escribe al archivo interno de la app === */
static void diag_write(const char *msg) {
    const char *paths[] = {
        "/data/data/com.eliasgt.agenda.agendareuniones/files/startc_diag.txt",
        "/data/user/0/com.eliasgt.agenda.agendareuniones/files/startc_diag.txt",
        NULL
    };
    for (int i = 0; paths[i]; i++) {
        FILE *f = fopen(paths[i], "a");
        if (f) {
            fputs(msg, f);
            fputs("\n", f);
            fflush(f);
            fclose(f);
            return;
        }
    }
}
/* === FIN DIAGNOSTICO === */
"""
    last_include = src.rfind('\n#include ')
    if last_include != -1:
        end_of_include = src.find('\n', last_include + 1)
        src = src[:end_of_include + 1] + DIAG_FUNC + src[end_of_include + 1:]
        print('  Funcion diag_write() insertada')
    else:
        print('  WARN: no se encontraron #include en start.c')

    # FIX: env_argument puede llegar NULL si Java aun no seteo
    # ANDROID_ARGUMENT (race condition). Debe corregirse INMEDIATAMENTE
    # despues de leerlo, antes de su primer uso (setenv ANDROID_APP_PATH
    # unas lineas mas abajo ya lo desreferencia).
    pat_read_argument = 'env_argument = getenv("ANDROID_ARGUMENT");'
    if pat_read_argument in src:
        FIX_NULL_ARGUMENT = '''  if (!env_argument || env_argument[0] == '\\0') {
    const char *_pkg = "com.eliasgt.agenda.agendareuniones";
    static char _fix_path[256];
    struct stat _fix_st;
    snprintf(_fix_path, sizeof(_fix_path), "/data/user/0/%s/files/app", _pkg);
    if (stat(_fix_path, &_fix_st) != 0)
      snprintf(_fix_path, sizeof(_fix_path), "/data/data/%s/files/app", _pkg);
    env_argument = _fix_path;
    diag_write("FIX: ANDROID_ARGUMENT era NULL, usando ruta hardcoded");
  }
'''
        idx = src.find(pat_read_argument) + len(pat_read_argument)
        end_line = src.find('\n', idx) + 1
        src = src[:end_line] + FIX_NULL_ARGUMENT + src[end_line:]
        print('  FIX race condition ANDROID_ARGUMENT insertado')
    else:
        print('  WARN: lectura de ANDROID_ARGUMENT no encontrada en start.c')

    # Diagnostico de variables de entorno al inicio
    pat_entrypoint = 'env_entrypoint = getenv("ANDROID_ENTRYPOINT");'
    if pat_entrypoint in src:
        DIAG_ENV = '''    diag_write("=== START.C INICIO ===");
    {
        char _diag_buf[512];
        snprintf(_diag_buf, sizeof(_diag_buf), "ANDROID_ARGUMENT=%s", env_argument ? env_argument : "NULL");
        diag_write(_diag_buf);
        snprintf(_diag_buf, sizeof(_diag_buf), "ANDROID_ENTRYPOINT=%s", env_entrypoint ? env_entrypoint : "NULL");
        diag_write(_diag_buf);
    }
'''
        idx = src.find(pat_entrypoint) + len(pat_entrypoint)
        end_line = src.find('\n', idx) + 1
        src = src[:end_line] + DIAG_ENV + src[end_line:]
        print('  Diagnostico de env vars insertado')
    else:
        print('  WARN: lectura de ANDROID_ENTRYPOINT no encontrada en start.c')

    # Diagnostico antes/despues de PyRun_SimpleFile
    pat_run_file = 'ret = PyRun_SimpleFile'
    if pat_run_file in src:
        DIAG_BEFORE_RUN = '''    diag_write("Antes de PyRun_SimpleFile");
'''
        idx = src.find(pat_run_file)
        src = src[:idx] + DIAG_BEFORE_RUN + src[idx:]

        DIAG_AFTER_RUN = '''    {
        char _diag_buf[512];
        snprintf(_diag_buf, sizeof(_diag_buf), "PyRun_SimpleFile ret=%d PyErr=%d", ret, PyErr_Occurred() ? 1 : 0);
        diag_write(_diag_buf);
    }
'''
        run_file_pos = src.find(pat_run_file)
        fclose_pos = src.find('fclose(fd)', run_file_pos)
        if fclose_pos != -1:
            end_line = src.find('\n', fclose_pos) + 1
            src = src[:end_line] + DIAG_AFTER_RUN + src[end_line:]
            print('  Diagnostico antes/despues de PyRun_SimpleFile insertado')
        else:
            print('  WARN: fclose(fd) no encontrado despues de PyRun_SimpleFile')
    else:
        print('  WARN: PyRun_SimpleFile no encontrado en start.c')

    open(start_c_path, 'w').write(src)
    print('start.c parcheado')
else:
    print('WARN: start.c no encontrado (se parcheara al buildear cuando este disponible)')
