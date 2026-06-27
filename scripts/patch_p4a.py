"""
Parches para compilar con p4a master + Kivy 2.3.0:

1. Python 3.14 → 3.12.9
2. python.py: stdlib.zip con ZIP_STORED (sin compresión) para que zipimport
   no necesite zlib al inicio — sin esto Python no puede importar encodings
   durante la inicialización (HAVE_ZLIB_H no definido en cross-compile)
3. start.c: diagnóstico en archivo (no logcat)

Nota: el parche android:hardwareAccelerated="false" fue eliminado porque
SDL2 2.30.11 ya tiene el fix para Android 15.
"""

import re
import os
import glob

base = '.buildozer/android/platform/python-for-android/pythonforandroid/recipes'

# --- 1. hostpython3: parchear version a 3.12.9 ---
path = f'{base}/hostpython3/__init__.py'
c = open(path).read()
c = re.sub(r'version\s*=\s*[\'"][0-9.]+[\'"]', 'version = "3.12.9"', c, count=1)
c = re.sub(r'sha512sum\s*=\s*[\'"][^\'\"]*[\'"]', "sha512sum = ''", c)
c = re.sub(r'patches\s*=\s*\[[\s\S]*?\]', 'patches = []', c, count=1)
open(path, 'w').write(c)
print('hostpython3 parcheado a 3.12.9')

# --- 2. python3: parchear version a 3.12.9 ---
path = f'{base}/python3/__init__.py'
c = open(path).read()
c = re.sub(r"version\s*=\s*['\"][0-9.]+['\"]", "version = '3.12.9'", c, count=1)
c = re.sub(r"sha512sum\s*=\s*['\"][^'\"]*['\"]", "sha512sum = ''", c)

c = c.rstrip('\n') + '\n'
c += '\nclass _Py312Fix(Python3Recipe):\n'
c += '    version = "3.12.9"\n'
c += '    def apply_patches(self, arch, build_dir=None): pass\n'
c += 'Python3Recipe = _Py312Fix\n'
c += 'recipe = Python3Recipe()\n'
open(path, 'w').write(c)
print('python3 parcheado a 3.12.9')

# --- 3. python.py: forzar ZIP_STORED en stdlib.zip ---
# zipimport en C necesita HAVE_ZLIB_H para descomprimir DEFLATE.
# Si no está definido al compilar (cross-compile con NDK), Python no puede
# leer NINGUNA entrada de stdlib.zip → falla al importar encodings al init.
# Solución: usar ZIP_STORED (sin compresión) para que zipimport no necesite zlib.
python_py_paths = [
    '.buildozer/android/platform/python-for-android/pythonforandroid/python.py',
]
for python_py_path in python_py_paths:
    if os.path.exists(python_py_path):
        c = open(python_py_path).read()
        if 'ZIP_DEFLATED' in c:
            c = c.replace('ZIP_DEFLATED', 'ZIP_STORED')
            open(python_py_path, 'w').write(c)
            print(f'python.py parcheado: ZIP_DEFLATED → ZIP_STORED en stdlib.zip')
        else:
            print(f'python.py: ZIP_DEFLATED no encontrado (ya usa STORED o diferente método)')
        break
else:
    print('WARN: python.py no encontrado')

# --- 4. start.c: agregar diagnóstico en archivo para debugging sin logcat ---
# Buscar start.c en el bootstrap SDL2
start_c_paths = glob.glob(
    '.buildozer/android/platform/python-for-android/pythonforandroid/bootstraps/sdl2/build/src/main/jni/src/start.c'
)
if not start_c_paths:
    start_c_paths = glob.glob(
        '.buildozer/**/start.c', recursive=True
    )

if start_c_paths:
    start_c_path = start_c_paths[0]
    print(f'Parcheando start.c: {start_c_path}')
    src = open(start_c_path).read()

    # Función de diagnóstico a insertar al inicio del archivo (después de los includes)
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

    # Insertar después del último #include
    last_include = src.rfind('\n#include ')
    if last_include != -1:
        end_of_include = src.find('\n', last_include + 1)
        src = src[:end_of_include+1] + DIAG_FUNC + src[end_of_include+1:]
        print('  Función diag_write() insertada')
    else:
        print('  WARN: no se encontraron #include en start.c')

    # Insertar llamadas en puntos clave:
    # A) Después de leer env_argument (inicio de main)
    DIAG_ENV = '''    diag_write("=== START.C INICIO ===");
    {
        char _diag_buf[512];
        snprintf(_diag_buf, sizeof(_diag_buf), "ANDROID_ARGUMENT=%s", env_argument ? env_argument : "NULL");
        diag_write(_diag_buf);
        snprintf(_diag_buf, sizeof(_diag_buf), "ANDROID_ENTRYPOINT=%s", env_entrypoint ? env_entrypoint : "NULL");
        diag_write(_diag_buf);
        snprintf(_diag_buf, sizeof(_diag_buf), "ANDROID_UNPACK=%s", getenv("ANDROID_UNPACK") ? getenv("ANDROID_UNPACK") : "NULL");
        diag_write(_diag_buf);
        snprintf(_diag_buf, sizeof(_diag_buf), "PYTHONHOME=%s", getenv("PYTHONHOME") ? getenv("PYTHONHOME") : "NULL");
        diag_write(_diag_buf);
    }
'''
    # Insertar después de la lectura de env_entrypoint al inicio de main()
    # Buscar el patrón típico: env_entrypoint = getenv("ANDROID_ENTRYPOINT");
    pat_entrypoint = 'env_entrypoint = getenv("ANDROID_ENTRYPOINT")'
    if pat_entrypoint in src:
        idx = src.find(pat_entrypoint)
        end_line = src.find('\n', idx) + 1
        src = src[:end_line] + DIAG_ENV + src[end_line:]
        print('  Diagnóstico de env vars insertado')

    # B) ANTES de Py_InitializeFromConfig: FIX PYTHONHOME + diagnóstico
    FIX_BEFORE_INIT = '''    /* FIX: unset PYTHONHOME para que no interfiera con module_search_paths */
    /* Con module_search_paths_set=1, PYTHONHOME causa que Python busque encodings */
    /* en la ruta equivocada en lugar de buscar en stdlib.zip */
    unsetenv("PYTHONHOME");
    setenv("LANG", "C.UTF-8", 1);
    setenv("LC_ALL", "C.UTF-8", 1);
    {
        char _diag_pre[512];
        snprintf(_diag_pre, sizeof(_diag_pre),
            "pre-init: module_search_paths_set=%d PYTHONHOME_unset=1",
            config.module_search_paths_set);
        diag_write(_diag_pre);
        snprintf(_diag_pre, sizeof(_diag_pre), "python_bundle_dir=%s", python_bundle_dir);
        diag_write(_diag_pre);
    }
'''
    pat_py_init = 'Py_InitializeFromConfig(&config)'
    if pat_py_init in src:
        idx = src.find(pat_py_init)
        line_start = src.rfind('\n', 0, idx) + 1
        src = src[:line_start] + FIX_BEFORE_INIT + src[line_start:]
        print('  FIX PYTHONHOME + diagnóstico pre-init insertado')
    else:
        print('  WARN: Py_InitializeFromConfig no encontrado')

    # B2) Después de Py_InitializeFromConfig
    DIAG_INIT_OK = '''    diag_write("Py_InitializeFromConfig OK");
'''
    DIAG_INIT_FAIL = '''    {
        char _diag_buf[512];
        snprintf(_diag_buf, sizeof(_diag_buf), "Py_InitializeFromConfig FAIL: %s", status.err_msg ? status.err_msg : "?");
        diag_write(_diag_buf);
    }
'''
    # Buscar "Initialized python" LOGP que viene después del if de error
    pat_init_ok = 'LOGP("Initialized python")'
    if pat_init_ok in src:
        idx = src.find(pat_init_ok)
        src = src[:idx] + DIAG_INIT_OK + src[idx:]
        print('  Diagnóstico post-init-OK insertado')

    # Buscar el bloque de error de Py_InitializeFromConfig
    pat_init_err = 'LOGP("Python initialization failed:")'
    if pat_init_err in src:
        idx = src.find(pat_init_err)
        end_line = src.find('\n', idx) + 1
        src = src[:end_line] + DIAG_INIT_FAIL + src[end_line:]
        print('  Diagnóstico post-init-FAIL insertado')

    # C) Antes de PyRun_SimpleFile
    DIAG_BEFORE_RUN = '''    {
        char _diag_buf[512];
        snprintf(_diag_buf, sizeof(_diag_buf), "Antes PyRun_SimpleFile: entrypoint=%s cwd=...", entrypoint);
        diag_write(_diag_buf);
    }
'''
    # Buscar "PyRun_SimpleFile" - primera ocurrencia en el código (la llamada real)
    pat_run_file = 'ret = PyRun_SimpleFile'
    if pat_run_file in src:
        idx = src.find(pat_run_file)
        src = src[:idx] + DIAG_BEFORE_RUN + src[idx:]
        print('  Diagnóstico pre-PyRun_SimpleFile insertado')

    # D) Después de PyRun_SimpleFile con resultado
    DIAG_AFTER_RUN = '''    {
        char _diag_buf[512];
        snprintf(_diag_buf, sizeof(_diag_buf), "PyRun_SimpleFile ret=%d PyErr=%d", ret, PyErr_Occurred() ? 1 : 0);
        diag_write(_diag_buf);
    }
'''
    # Buscar fclose(fd) SOLO después del ret=PyRun_SimpleFile
    run_file_pos = src.find('ret = PyRun_SimpleFile')
    if run_file_pos != -1:
        fclose_pos = src.find('fclose(fd)', run_file_pos)
        if fclose_pos != -1:
            end_line = src.find('\n', fclose_pos) + 1
            src = src[:end_line] + DIAG_AFTER_RUN + src[end_line:]
            print('  Diagnóstico post-PyRun_SimpleFile insertado')
        else:
            print('  WARN: fclose(fd) no encontrado después de PyRun_SimpleFile')

    # E) FIX: si ANDROID_ARGUMENT es NULL (race condition Java-SDL), usar ruta hardcoded
    # + diagnóstico de CWD antes de chdir
    FIX_AND_CWD = '''    /* FIX race condition: si Java no seteó ANDROID_ARGUMENT aún, usar ruta hardcoded */
    if (!env_argument || env_argument[0] == '\\0') {
        const char *_pkg = "com.eliasgt.agenda.agendareuniones";
        static char _fix_path[256];
        struct stat _fix_st;
        snprintf(_fix_path, sizeof(_fix_path), "/data/user/0/%s/files/app", _pkg);
        if (stat(_fix_path, &_fix_st) != 0)
            snprintf(_fix_path, sizeof(_fix_path), "/data/data/%s/files/app", _pkg);
        env_argument = _fix_path;
        setenv("ANDROID_ARGUMENT", env_argument, 1);
        if (!getenv("ANDROID_UNPACK") || getenv("ANDROID_UNPACK")[0] == '\\0')
            setenv("ANDROID_UNPACK", env_argument, 1);
        diag_write("FIX: ANDROID_ARGUMENT era NULL, usando ruta hardcoded");
        {
            char _diag_buf2[512];
            snprintf(_diag_buf2, sizeof(_diag_buf2), "FIX ANDROID_ARGUMENT=%s", env_argument);
            diag_write(_diag_buf2);
        }
    }
    {
        char _cwd_buf[512];
        char _diag_buf[512];
        if (getcwd(_cwd_buf, sizeof(_cwd_buf)) != NULL)
            snprintf(_diag_buf, sizeof(_diag_buf), "CWD_ANTES_CHDIR=%s", _cwd_buf);
        else
            snprintf(_diag_buf, sizeof(_diag_buf), "CWD_ANTES_CHDIR=ERROR");
        diag_write(_diag_buf);
    }
'''
    pat_chdir = 'chdir(env_argument)'
    if pat_chdir in src:
        idx = src.find(pat_chdir)
        line_start = src.rfind('\n', 0, idx) + 1
        src = src[:line_start] + FIX_AND_CWD + src[line_start:]
        print('  FIX race condition + diagnóstico CWD insertado')
    else:
        print('  WARN: chdir(env_argument) no encontrado en start.c')

    open(start_c_path, 'w').write(src)
    print('start.c parcheado con diagnósticos + FIX race condition')
else:
    print('WARN: start.c no encontrado (se parcheará al buildear cuando esté disponible)')
