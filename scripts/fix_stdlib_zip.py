#!/usr/bin/env python3
"""Post-procesa el APK para recomprimir stdlib.zip como ZIP_STORED."""
import zipfile, tarfile, gzip, io, glob, sys, os

apks = glob.glob('bin/*.apk')
if not apks:
    print("ERROR: No APK encontrado en bin/")
    sys.exit(1)
apk_path = apks[0]
print(f"APK: {apk_path} ({os.path.getsize(apk_path):,} bytes)")

with open(apk_path, 'rb') as f:
    apk_data = f.read()

apk_zip = zipfile.ZipFile(io.BytesIO(apk_data), 'r')
print(f"Entradas en APK: {len(apk_zip.namelist())}")

# Buscar libpybundle.so
pybundle_name = next((n for n in apk_zip.namelist() if 'libpybundle' in n), None)
if not pybundle_name:
    print("WARN: libpybundle.so no encontrado, listando lib/:")
    for n in apk_zip.namelist():
        if n.startswith('lib/'):
            print(f"  {n}")
    sys.exit(1)

print(f"Leyendo: {pybundle_name}")
pybundle_data = apk_zip.read(pybundle_name)
print(f"  Tamaño: {len(pybundle_data):,} bytes, primeros bytes: {pybundle_data[:4].hex()}")

# Descomprimir gzip
try:
    with gzip.open(io.BytesIO(pybundle_data)) as gz:
        tar_data = gz.read()
    print(f"  gzip OK, tar size: {len(tar_data):,} bytes")
except Exception as e:
    print(f"ERROR: gzip falló: {e}")
    print(f"  Primeros 16 bytes: {pybundle_data[:16].hex()}")
    sys.exit(1)

# Abrir tar
try:
    tf = tarfile.open(fileobj=io.BytesIO(tar_data))
    members = tf.getmembers()
    print(f"  Miembros en tar: {len(members)}")
    for m in members[:5]:
        print(f"    {m.name} ({m.size} bytes)")
except Exception as e:
    print(f"ERROR: tarfile falló: {e}")
    sys.exit(1)

# Buscar stdlib.zip
stdlib_member = next((m for m in members if 'stdlib.zip' in m.name), None)
if not stdlib_member:
    print("ERROR: stdlib.zip no encontrado en tar. Miembros:")
    for m in members:
        print(f"  {m.name}")
    sys.exit(1)

print(f"stdlib.zip encontrado: {stdlib_member.name} ({stdlib_member.size:,} bytes)")
stdlib_data = tf.extractfile(stdlib_member).read()

# Verificar compresion actual
old_zf = zipfile.ZipFile(io.BytesIO(stdlib_data))
all_entries = old_zf.infolist()
deflated = [i for i in all_entries if i.compress_type != 0]
stored = [i for i in all_entries if i.compress_type == 0]
print(f"stdlib.zip: {len(deflated)} DEFLATED, {len(stored)} STORED de {len(all_entries)} total")

if not deflated:
    print("stdlib.zip ya es ZIP_STORED, no se necesitan cambios.")
    sys.exit(0)

# Recomprimir como STORED
print(f"Convirtiendo {len(deflated)} entradas a ZIP_STORED...")
new_stdlib = io.BytesIO()
with zipfile.ZipFile(new_stdlib, 'w', compression=zipfile.ZIP_STORED) as new_zf:
    for info in all_entries:
        data = old_zf.read(info.filename)
        new_zf.writestr(info, data)
new_stdlib_data = new_stdlib.getvalue()
print(f"stdlib.zip nuevo: {len(new_stdlib_data):,} bytes (era {len(stdlib_data):,})")

# Reconstruir tar
print("Reconstruyendo tar...")
new_tar = io.BytesIO()
with tarfile.open(fileobj=new_tar, mode='w') as new_tf:
    for member in members:
        if 'stdlib.zip' in member.name:
            info = tarfile.TarInfo(name=member.name)
            info.size = len(new_stdlib_data)
            info.mode = member.mode
            info.mtime = member.mtime
            info.uid = member.uid
            info.gid = member.gid
            new_tf.addfile(info, io.BytesIO(new_stdlib_data))
        else:
            try:
                fileobj = tf.extractfile(member)
                if fileobj is not None:
                    new_tf.addfile(member, fileobj)
                else:
                    new_tf.addfile(member)
            except Exception as e:
                print(f"  WARN: {member.name}: {e}")

# Recomprimir como gzip
print("Comprimiendo tar como gzip...")
new_pybundle_buf = io.BytesIO()
with gzip.GzipFile(fileobj=new_pybundle_buf, mode='wb') as gz:
    gz.write(new_tar.getvalue())
new_pybundle_data = new_pybundle_buf.getvalue()
print(f"libpybundle.so nuevo: {len(new_pybundle_data):,} bytes")

# Actualizar APK
print("Actualizando APK...")
new_apk_buf = io.BytesIO()
with zipfile.ZipFile(io.BytesIO(apk_data), 'r') as old_apk:
    with zipfile.ZipFile(new_apk_buf, 'w', compression=zipfile.ZIP_STORED) as new_apk_zip:
        for item in old_apk.infolist():
            if item.filename == pybundle_name:
                new_apk_zip.writestr(item, new_pybundle_data)
            else:
                new_apk_zip.writestr(item, old_apk.read(item.filename))

with open(apk_path, 'wb') as f:
    f.write(new_apk_buf.getvalue())
print(f"APK actualizado: {apk_path} ({os.path.getsize(apk_path):,} bytes)")
print("EXITO: stdlib.zip convertido a ZIP_STORED en el APK")
