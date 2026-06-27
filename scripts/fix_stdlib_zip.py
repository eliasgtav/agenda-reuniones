#!/usr/bin/env python3
"""Post-procesa el APK para recomprimir stdlib.zip como ZIP_STORED.

Esto evita el problema de la cache de buildozer: aunque p4a use un stdlib.zip
con DEFLATE del cache, este script lo reemplaza por STORED directamente en el APK.
"""
import zipfile, tarfile, gzip, io, glob, sys, os

apks = glob.glob('bin/*.apk')
if not apks:
    print("ERROR: No APK encontrado en bin/")
    sys.exit(1)
apk_path = apks[0]
print(f"Procesando APK: {apk_path}")

with open(apk_path, 'rb') as f:
    apk_data = f.read()

apk_zip = zipfile.ZipFile(io.BytesIO(apk_data), 'r')

pybundle_name = next((n for n in apk_zip.namelist() if 'libpybundle.so' in n), None)
if not pybundle_name:
    print("ERROR: libpybundle.so no encontrado en APK")
    sys.exit(1)

print(f"Encontrado: {pybundle_name}")
pybundle_data = apk_zip.read(pybundle_name)

with gzip.open(io.BytesIO(pybundle_data)) as gz:
    tar_data = gz.read()

tf = tarfile.open(fileobj=io.BytesIO(tar_data))

stdlib_member = next((m for m in tf.getmembers() if m.name.endswith('stdlib.zip')), None)
if not stdlib_member:
    print("ERROR: stdlib.zip no encontrado en libpybundle.so")
    sys.exit(1)

stdlib_data = tf.extractfile(stdlib_member).read()
old_zf = zipfile.ZipFile(io.BytesIO(stdlib_data))
deflated = [i for i in old_zf.infolist() if i.compress_type != 0]
print(f"stdlib.zip: {len(deflated)} DEFLATED, {len(old_zf.infolist()) - len(deflated)} STORED")

if not deflated:
    print("stdlib.zip ya es ZIP_STORED, no se necesitan cambios.")
    sys.exit(0)

print(f"Convirtiendo {len(deflated)} entradas a ZIP_STORED...")
new_stdlib = io.BytesIO()
with zipfile.ZipFile(new_stdlib, 'w', compression=zipfile.ZIP_STORED) as new_zf:
    for info in old_zf.infolist():
        data = old_zf.read(info.filename)
        new_zf.writestr(info, data)
new_stdlib_data = new_stdlib.getvalue()
print(f"stdlib.zip nuevo: {len(new_stdlib_data):,} bytes (era {len(stdlib_data):,} bytes)")

new_tar = io.BytesIO()
with tarfile.open(fileobj=new_tar, mode='w') as new_tf:
    for member in tf.getmembers():
        if member.name.endswith('stdlib.zip'):
            info = tarfile.TarInfo(name=member.name)
            info.size = len(new_stdlib_data)
            info.mode = member.mode
            info.mtime = member.mtime
            new_tf.addfile(info, io.BytesIO(new_stdlib_data))
        else:
            fileobj = tf.extractfile(member)
            if fileobj is not None:
                new_tf.addfile(member, fileobj)
            else:
                new_tf.addfile(member)

new_pybundle_buf = io.BytesIO()
with gzip.GzipFile(fileobj=new_pybundle_buf, mode='wb') as gz:
    gz.write(new_tar.getvalue())
new_pybundle_data = new_pybundle_buf.getvalue()
print(f"libpybundle.so nuevo: {len(new_pybundle_data):,} bytes")

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
print(f"APK actualizado con stdlib.zip ZIP_STORED: {apk_path}")
