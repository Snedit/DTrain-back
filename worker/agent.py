import os, time, io, zipfile, tempfile, shutil, subprocess, json, sys
from urllib.parse import urljoin
import requests
# import cloudinary
# import cloudinary.uploader

import tarfile 
# Optional: use docker SDK if available, but we can shell out for simplicity
try:
    import docker
    DOCKER_SDK = True
except Exception:
    DOCKER_SDK = False

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def api_get(cfg, path):
    url = urljoin(cfg["server_url"], path)
    headers = {"Authorization": f"Bearer {cfg['token']}"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def api_post(cfg, path, json_body=None):
    url = urljoin(cfg["server_url"], path)
    headers = {"Authorization": f"Bearer {cfg['token']}", "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, json=json_body, timeout=60)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {}

def ask_user_acceptance(job):
    """Ask user if they want to accept this job"""
    print(f"\n{'='*50}")
    print(f"📋 NEW JOB AVAILABLE")
    print(f"   ID: {job['id']}")
    print(f"   Name: {job['name']}")
    print(f"   Main Entry: {job.get('main_entry', 'main.py')}")
    print(f"   Requirements: {job.get('requirements_file', 'requirements.txt')}")
    print(f"{'='*50}")
    
    while True:
        response = input("Accept this job? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'")

def download_bundle(cfg, bundle_filename, out_path):
    url = urljoin(cfg["server_url"], f"/api/jobs/{bundle_filename}/download")  # not used; we use by job id instead
    # We'll receive the direct /api/jobs/<id>/download route.
    raise RuntimeError("Use download_job_by_id instead")

def download_job_by_id(cfg, job_id, out_zip):
    url = urljoin(cfg["server_url"], f"/api/jobs/{job_id}/download")
    headers = {"Authorization": f"Bearer {cfg['token']}"}
    with requests.get(url, headers=headers, timeout=300, stream=True) as r:
        r.raise_for_status()
        with open(out_zip, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

def decompress(zip_path, dest_dir):
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(dest_dir)

def send_logs(cfg, job_id, lines):
    if not lines:
        return
    try:
        api_post(cfg, f"/api/jobs/{job_id}/logs", {"lines": lines})
    except Exception as e:
        print(f"Failed to send logs: {e}", flush=True)

def build_image(context_dir, tag):
    dockerfile_path = os.path.join(context_dir, "Dockerfile")
    use_builtin = not os.path.exists(dockerfile_path)
    if use_builtin:
        # Write a simple Dockerfile (server provides a similar base)
        with open(os.path.join(context_dir, "Dockerfile"), "w") as f:
            f.write("""FROM python:3.8
WORKDIR /app
COPY . /app
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi
CMD ["python", "main.py"]
""")
    print(f"Building Docker image {tag} ...", flush=True)
    if DOCKER_SDK:
        client = docker.from_env()
        # build generator stream
        image, logs = client.images.build(path=context_dir, tag=tag, rm=True)
    else:
        # fallback to CLI
        proc = subprocess.Popen(["docker", "build", "-t", tag, context_dir], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in iter(proc.stdout.readline, ''):
            print(line, end='')
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError("docker build failed")
    return tag

def upload_model_file(cfg, job_id, file_path):
    print("uploading files to ")
    url = urljoin(cfg["server_url"], f"/api/jobs/{job_id}/upload_model")
    headers = {"Authorization": f"Bearer {cfg['token']}"}
    
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f)}
        r = requests.post(url, headers=headers, files=files, timeout=120)
        r.raise_for_status()
        return r.json()
    

def extract_model_files(container, workdir, model_patterns=None):
    """Extract model files from container to local directory"""
    if model_patterns is None:
        model_patterns = ["*.pkl", "*.joblib", "*.h5", "*.pth", "*.pt", "model*"]
    
    extracted_files = []
    
    if DOCKER_SDK:
        # Using Docker SDK
        for pattern in model_patterns:
            try:
                # Get files from container
                tar_stream, _ = container.get_archive(f'/app/{pattern}')
                # Extract to workdir
                with tempfile.NamedTemporaryFile() as tmp:
                    for chunk in tar_stream:
                        tmp.write(chunk)
                    tmp.flush()
                    
                    with tarfile.open(tmp.name, 'r') as tar:
                        tar.extractall(workdir)
                        extracted_files.extend([os.path.join(workdir, name) for name in tar.getnames()])
            except Exception:
                continue  # Pattern not found, try next
    else:
        # Using CLI - copy files out of container
        for pattern in model_patterns:
            try:
                subprocess.run([
                    "docker", "cp", f"{container}:/app/{pattern}", workdir
                ], check=False, capture_output=True)  # Don't fail if pattern doesn't match
                
                # Check what files were copied
                for f in os.listdir(workdir):
                    if any(f.endswith(ext.replace('*', '')) for ext in model_patterns):
                        extracted_files.append(os.path.join(workdir, f))
            except Exception:
                continue
    
    return extracted_files

def run_container(tag, main_entry="main.py", env=None, network=None):
    env_list = [f"{k}={v}" for k,v in (env or {}).items()]
    cmd = ["python", main_entry]

    # Ensure local outputs dir exists
    outputs_dir = os.path.abspath("outputs")
    os.makedirs(outputs_dir, exist_ok=True)

    if DOCKER_SDK:
        client = docker.from_env()
        container = client.containers.run(
            tag,
            cmd,
            detach=True,
            environment=env or {},
            network=network,
            volumes={
                outputs_dir: {"bind": "/app/outputs", "mode": "rw"}
            }
        )
        return container
    else:
        args = ["docker", "run", "-d"]
        for e in env_list:
            args += ["-e", e]
        if network:
            args += ["--network", network]

        # mount outputs folder
        args += ["-v", f"{outputs_dir}:/app/outputs"]

        args += [tag] + cmd
        cid = subprocess.check_output(args, text=True).strip()
        return cid

        
def stream_logs(container, job_id, cfg):
    if DOCKER_SDK:
        for line in container.logs(stream=True, follow=True):
            print(line, flush=True)
            send_logs(cfg, job_id, [line.decode('utf-8', errors='ignore').rstrip()])
    else:
        proc = subprocess.Popen(["docker", "logs", "-f", str(container)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
        for line in iter(proc.stdout.readline, ''):
            send_logs(cfg, job_id, [line.rstrip()])
        proc.wait()
# def upload_to_cloudinary(file_path):
#         result = cloudinary.uploader.upload(file_path, resource_type="raw")
#         return result["public_id"], result["secure_url"]
def main():
    cfg = load_config()
    # Register worker
    try:
        api_post(cfg, "/api/workers/register", {"name": cfg["worker_name"]})
    except Exception as e:
        print(f"Register failed: {e}")
    while True:
        try:
            pending = api_get(cfg, "/api/jobs/pending")
        except Exception as e:
            print(f"Poll failed: {e}")
            time.sleep(cfg.get("poll_interval_sec", 5))
            continue

        if not pending:
            print("⏳ No pending jobs... waiting")
            time.sleep(cfg.get("poll_interval_sec", 5))
            continue

        job = pending[0]
        job_id = job["id"]
        
        # Ask user for manual acceptance
        if not ask_user_acceptance(job):
            print("❌ Job rejected by user")
            time.sleep(cfg.get("poll_interval_sec", 5))
            continue
            
        print(f"✅ Accepting job {job_id} ...")
        try:
            api_post(cfg, f"/api/jobs/{job_id}/accept", {"worker_name": cfg["worker_name"]})
        except Exception as e:
            print(f"❌ Accept failed: {e}")
            time.sleep(cfg.get("poll_interval_sec", 5))
            continue

        # Download
        tmpdir = tempfile.mkdtemp(prefix=f"job_{job_id}_")
        bundle_zip = os.path.join(tmpdir, "bundle.zip")
        try:
            download_job_by_id(cfg, job_id, bundle_zip)
            workdir = os.path.join(tmpdir, "context")
            os.makedirs(workdir, exist_ok=True)
            decompress(bundle_zip, workdir)
            tag = job.get("docker_image_tag") or f"mljob-{job_id}:latest"
            api_post(cfg, f"/api/jobs/{job_id}/status", {"status":"running", "note": "Building Docker image"})
            build_image(workdir, tag)
            api_post(cfg, f"/api/jobs/{job_id}/status", {"status":"running", "note": "Starting container"})
            container = run_container(tag, main_entry=job.get("main_entry","main.py"), env=cfg.get("docker_run_env") or {}, network=cfg.get("docker_network"))
            api_post(cfg, f"/api/jobs/{job_id}/status", {"status":"running", "note": "Streaming logs"})
            stream_logs(container, job_id, cfg)
            api_post(cfg, f"/api/jobs/{job_id}/status", {"status":"completed", "note": "Container finished"})
            api_post(cfg, f"/api/jobs/{job_id}/status", {"status":"completed", "note": "Container finished"})

# Look for generated files in outputs/
            outputs_dir = os.path.abspath("outputs")
            print("output dir = " + outputs_dir)
            for fname in os.listdir(outputs_dir):
                fpath = os.path.join(outputs_dir, fname)
                if os.path.isfile(fpath):
                    try:
                        res = upload_model_file(cfg, job_id, fpath)
                        print(f"✅ Uploaded {fname} -> {res}")
                        print("removing the file after this: ")
                        os.remove(fpath)
                        print("successfully removed: ")
                    except Exception as e:
                        print(f"❌ Failed to upload {fname}: {e}")
        except Exception as e:
            print(f"Job {job_id} failed: {e}")
            send_logs(cfg, job_id, [f"[WORKER ERROR] {e}"])
            try:
                api_post(cfg, f"/api/jobs/{job_id}/status", {"status":"failed", "note": str(e)})
            except Exception:
                pass
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

if __name__ == "__main__":
    main()
