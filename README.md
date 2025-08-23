# Decentralized ML Training — Demo App

This is a minimal end-to-end example showing a Flask server that accepts ML training jobs as `.zip` bundles and a Python worker agent that accepts and runs those jobs in Docker, streaming logs back to the server UI in real time via Socket.IO.

> ⚠️ Security note: This is a **demo**. Do not run untrusted code without sandboxing and proper isolation. Add authentication, per-worker tokens, resource limits, etc.

## Project layout

```
decentralized-ml-app/
├─ server/                    # Flask + Socket.IO backend and simple web UI
│  ├─ app.py
│  ├─ models.py
│  ├─ utils.py
│  ├─ config.py
│  ├─ requirements.txt
│  ├─ docker/base.Dockerfile
│  ├─ templates/
│  └─ static/
├─ worker/                    # Worker agent that pulls jobs, builds & runs Docker, streams logs
│  ├─ agent.py
│  ├─ requirements.txt
│  └─ config.example.json
└─ example_job/               # Example training job bundle
   ├─ main.py
   └─ requirements.txt
```

## Quick start

### 1) Server

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export WORKER_SHARED_TOKEN="changeme-worker-token"
python app.py
```

- Open http://localhost:5000
- Submit a job by uploading a `.zip` of your code (see `example_job`).
- Open the job page to view real-time logs.

### 2) Worker

On each worker machine (must have Docker installed):

```bash
cd worker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
# edit server_url and token in config.json
python agent.py
```

The worker will register with the server, poll for pending jobs, accept the first one, download the bundle, build a Docker image, run the container, and stream logs back.

### Job bundle format

Upload a `.zip` containing your training code with at least:

- `main.py` — the entry file (customizable on upload)
- `requirements.txt` — Python dependencies

The worker will build a Docker image with your code as the context (using `server/docker/base.Dockerfile` as template). If your bundle includes its own `Dockerfile`, the worker will prefer that.

### Notes & TODOs

- Add per-worker authentication and HTTPS.
- Push/pull images from a registry instead of local build per worker.
- Support dataset mounting, resource limits (CPU/GPU), and cancellation.
- Replace polling with a pub/sub queue if desired.
