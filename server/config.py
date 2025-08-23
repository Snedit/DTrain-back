import os

# Basic config (for demo only; use env vars in production)
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///app.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Where uploaded job zips are stored
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(os.path.dirname(__file__), "uploads"))
JOB_BUNDLES_FOLDER = os.environ.get("JOB_BUNDLES_FOLDER", os.path.join(os.path.dirname(__file__), "job_bundles"))

# Simple shared token for worker auth (demo only)
WORKER_SHARED_TOKEN = os.environ.get("WORKER_SHARED_TOKEN", "changeme-worker-token")
