import os, zipfile, uuid
from flask import current_app

def save_upload(file_storage, subdir=""):
    os.makedirs(current_app.config["JOB_BUNDLES_FOLDER"], exist_ok=True)
    unique = uuid.uuid4().hex
    filename = f"{unique}.zip"
    path = os.path.join(current_app.config["JOB_BUNDLES_FOLDER"], filename)
    file_storage.save(path)
    return filename, path

def zip_dir(source_dir, out_zip_path):
    with zipfile.ZipFile(out_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(source_dir):
            for f in files:
                abs_path = os.path.join(root, f)
                rel_path = os.path.relpath(abs_path, source_dir)
                zf.write(abs_path, rel_path)
