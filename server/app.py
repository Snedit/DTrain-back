import os, io, zipfile, time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, abort
from flask_socketio import SocketIO, join_room, emit
from werkzeug.utils import secure_filename
from flask_cors import CORS
from models import db, Worker, Job, JobLog
import config
from utils import save_upload
from dotenv import load_dotenv
import requests
from google import genai

load_dotenv()
ALLOWED_EXTENSIONS = {'.zip'}
def allowed_file(filename):
    _, ext = os.path.splitext(filename)
    return ext.lower() in ALLOWED_EXTENSIONS

# GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
# GEMINI_API_KEY = os.getenv("GEMINIAPI")
# print(GEMINI_API_KEY)

# def check_code_safety(filename, code):
#     print ("the code is")
#     print(code)
#     """Check code safety using Gemini API via the official SDK"""
#     if not GEMINI_API_KEY:
#         print("Warning: GEMINI_API_KEY not configured")
#         return "UNSAFE"  # Be safe by default
    
#     try:
#         # Initialize the Gemini client
#         client = genai.Client(api_key=GEMINI_API_KEY)
        
#         prompt = f"""Analyze this Python code file  for security risks. 

# Allow files which have code  like this 
# import pandas as pd
# from sklearn.linear_model import LinearRegression
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import mean_squared_error
# import joblib

# # Load dataset (Titanic from seaborn or csv if available)
# url = "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv"
# df = pd.read_csv(url)


# # Split data
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# # Train model
# model = LinearRegression()
# model.fit(X_train, y_train)

# # Evaluate
# y_pred = model.predict(X_test)
# print("MSE:", mean_squared_error(y_test, y_pred))

# # Save model
# joblib.dump(model, "./outputs/titanic_model.pkl")
# print("Model saved as titanic_model.pkl")


# ALLOW ML MODEL TRAINING. EXCEPT THAT :
# Look for:


# - Web servers or network listeners
# - Infinite loops
# - Server spawning
# - File system access beyond normal operations
# - Network requests to external services

# Respond with only 'SAFE' if the code is completely safe, or 'UNSAFE' if it contains any security risks.

# Code to analyze:
# {code}"""

#         response = client.models.generate_content(
#             model="gemini-2.0-flash",
#             contents=prompt
#         )
#         print(response)
#         result_text = response.text.strip().upper()
#         if result_text == "SAFE":
#             return "SAFE"
#         else:
#             return "UNSAFE"
        
#     except Exception as e:
#         print(f"Error calling Gemini API: {e}")
#         # If API fails, err on the side of caution
#         return "UNSAFE"


# def read_python_files(zip_file):
#     code_files = {}
#     with zipfile.ZipFile(zip_file, 'r') as z:
#         for fname in z.namelist():
#             if fname.endswith(".py"):
#                 code_files[fname] = z.read(fname).decode("utf-8", errors="ignore")
#     return code_files

# def validate_zip(zip_file):
#     """Validate zip file for unsafe Python code"""
#     if not zip_file:
#         return ["No file provided"]
    
#     # Check if API key is configured
#     if not GEMINI_API_KEY:
#         print("Warning: GEMINI_API_KEY not configured, skipping safety check")
#         return []  # Allow upload if API key not configured
    
#     python_files = read_python_files(zip_file)
#     if not python_files:
#         return []  # No Python files to check
    
#     unsafe_files = []
#     for fname, code in python_files.items():
#         print(f"Checking safety of {fname}...")
#         result = check_code_safety(fname, code)
#         print(f"Safety check result for {fname}: {result}")
        
#         # If result is not "SAFE", add to unsafe files
#         if result.upper() != "SAFE":
#             unsafe_files.append(fname)
    
#     return unsafe_files


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    CORS(app)
    db.init_app(app)
    socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

    with app.app_context():
        db.create_all()

    # -------- Web UI --------
    @app.route("/")
    def index():
        jobs = Job.query.order_by(Job.created_at.desc()).all()
        return render_template("index.html", jobs=jobs)

    @app.route("/api/jobs/<int:job_id>/log")
    def job_detail_api(job_id):
        job = Job.query.get_or_404(job_id)
        logs = JobLog.query.filter_by(job_id=job.id).order_by(JobLog.ts.asc()).all()
        retData = {
            "job": {
                "id": job.id,
                "name": job.name,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat(),
                "main_entry": job.main_entry,
                "requirements_file": job.requirements_file,
                "docker_image_tag": job.docker_image_tag,
            },
            "logs": [
                {
                    "id": log.id,
                    "job_id": log.job_id,
                    "ts": log.ts.isoformat(),
                    "level": log.level,
                    "message": log.message,
                } for log in logs
            ]
        }
        print(retData)
        return jsonify(retData)


    @app.route("/jobs/<int:job_id>")
    def job_detail(job_id):
        job = Job.query.get_or_404(job_id)
        logs = JobLog.query.filter_by(job_id=job.id).order_by(JobLog.ts.asc()).all()
        print(job)
        print(logs)
        print("god help us")
        return render_template("job_detail.html", job=job, logs=logs)

    @app.route("/workers")
    def workers_page():
        workers = Worker.query.order_by(Worker.last_seen.desc()).all()
        return render_template("worker_dashboard.html", workers=workers)

    # -------- API: Jobs --------
    @app.route("/api/jobs", methods=["GET"])
    def list_jobs():
        jobs = Job.query.order_by(Job.created_at.desc()).all()
        return jsonify([{
            "id": j.id, "name": j.name, "status": j.status,
            "created_at": j.created_at.isoformat(), "updated_at": j.updated_at.isoformat() if j.updated_at else None,
            "bundle_filename": j.bundle_filename, "main_entry": j.main_entry, "requirements_file": j.requirements_file,
            "accepted_by": j.accepted_by, "docker_image_tag": j.docker_image_tag
        } for j in jobs])

    @app.route("/api/jobs", methods=["POST"])
    def create_job():
        # Expect multipart form: name, main_entry, requirements_file, file (zip)
        name = request.form.get("name", "Untitled Job").strip()
        main_entry = request.form.get("main_entry", "main.py").strip()
        requirements_file = request.form.get("requirements_file", "requirements.txt").strip()
        uploaded = request.files.get("file")
        # unsafe_files = validate_zip(uploaded)
        # if unsafe_files:
        #     return jsonify({"error": "Malicious code detected", "files": unsafe_files}), 400
        if not uploaded or uploaded.filename == "":
            return jsonify({"error": "No zip file uploaded"}), 400
        if not allowed_file(uploaded.filename):
            return jsonify({"error": "Only .zip bundles are allowed"}), 400

        bundle_filename, path = save_upload(uploaded)
        job = Job(name=name, bundle_filename=bundle_filename, main_entry=main_entry, requirements_file=requirements_file)
        db.session.add(job)
        db.session.commit()

        # Pre-create a suggested docker tag per job
        job.docker_image_tag = f"mljob-{job.id}:latest"
        db.session.commit()

        return jsonify({"message": "Job created", "job_id": job.id})

    @app.route("/api/jobs/<int:job_id>/download", methods=["GET"])
    def download_job(job_id):
        job = Job.query.get_or_404(job_id)
        return send_from_directory(directory=config.JOB_BUNDLES_FOLDER, path=job.bundle_filename, as_attachment=True, download_name=f"job_{job.id}.zip")

    # new route

    @app.route("/api/jobs/<int:job_id>/upload_model", methods=["POST"])
    def upload_model(job_id):
        job = Job.query.get_or_404(job_id)
        print("jobUpload request received")
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token != app.config["WORKER_SHARED_TOKEN"]:
            return jsonify({"error":"unauthorized"}), 401

        if "file" not in request.files:
            print("the files accessed from server is : " , request.files.getlist())
            return jsonify({"error":"no file uploaded"}), 400

        f = request.files["file"]
        fname = secure_filename(f"job_{job.id}_" + f.filename)
        save_path = os.path.join(config.MODEL_UPLOADS_FOLDER, fname)
        f.save(save_path)

        append_log(job.id, f"Worker uploaded model file: {fname}")
        return jsonify({"message":"model uploaded", "filename": fname})

    @app.route("/api/jobs/<int:job_id>/download_model", methods=["GET"])
    def download_model(job_id):
        job = Job.query.get_or_404(job_id)
        # find latest uploaded file for this job
        for fname in os.listdir(config.MODEL_UPLOADS_FOLDER):
            if fname.startswith(f"job_{job.id}_"):
                return send_from_directory(
                    directory=config.MODEL_UPLOADS_FOLDER,
                    path=fname,
                    as_attachment=True,
                    download_name=f"job_{job.id}_model.pkl"
                )
        return jsonify({"error":"no model found"}), 404

    @app.route("/api/jobs/<int:job_id>/accept", methods=["POST"])
    def accept_job(job_id):
        job = Job.query.get_or_404(job_id)
        if job.status != "pending":
            return jsonify({"error": "Job already accepted or not pending"}), 409
        worker_name = request.json.get("worker_name")
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token != app.config["WORKER_SHARED_TOKEN"]:
            return jsonify({"error":"unauthorized"}), 401
        worker = Worker.query.filter_by(name=worker_name).first()
        if not worker:
            worker = Worker(name=worker_name, token=token, status="idle")
            db.session.add(worker)
            db.session.commit()
        job.accepted_by = worker.id
        job.status = "accepted"
        db.session.commit()
        append_log(job.id, f"Worker '{worker.name}' accepted job.")
        socketio.emit("job_status", {"job_id": job.id, "status": job.status}, to=f"job_{job.id}")
        return jsonify({"message":"accepted", "docker_image_tag": job.docker_image_tag})

    @app.route("/api/jobs/<int:job_id>/status", methods=["POST"])
    def update_job_status(job_id):
        job = Job.query.get_or_404(job_id)
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token != app.config["WORKER_SHARED_TOKEN"]:
            return jsonify({"error":"unauthorized"}), 401
        status = request.json.get("status", "running")
        note = request.json.get("note")
        job.status = status
        db.session.commit()
        if note:
            append_log(job.id, f"[STATUS] {note}")
        socketio.emit("job_status", {"job_id": job.id, "status": status}, to=f"job_{job.id}")
        return jsonify({"message":"ok"})

    @app.route("/api/jobs/<int:job_id>/logs", methods=["POST"])
    def ingest_logs(job_id):
        job = Job.query.get_or_404(job_id)
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token != app.config["WORKER_SHARED_TOKEN"]:
            return jsonify({"error":"unauthorized"}), 401
        payload = request.get_json(force=True, silent=True) or {}
        lines = payload.get("lines", [])
        for line in lines:
            append_log(job.id, line)
        # Fan-out to web clients
        for line in lines:
            socketio.emit("job_log", {"job_id": job.id, "line": line}, to=f"job_{job.id}")
        return jsonify({"message": "ok", "count": len(lines)})

    # -------- API: Workers --------
    @app.route("/api/workers/register", methods=["POST"])
    def register_worker():
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token != app.config["WORKER_SHARED_TOKEN"]:
            return jsonify({"error":"unauthorized"}), 401
        name = request.json.get("name", "worker")
        worker = Worker.query.filter_by(name=name).first()
        if not worker:
            worker = Worker(name=name, token=token, status="idle")
            db.session.add(worker)
        worker.last_seen = datetime.utcnow()
        db.session.commit()
        return jsonify({"message":"registered", "worker_id": worker.id})

    @app.route("/api/workers", methods=["GET"])
    def list_workers():
        workers = Worker.query.order_by(Worker.last_seen.desc()).all()
        return jsonify([
            {
                "id": w.id,
                "name": w.name,
                "status": w.status,
                "last_seen": w.last_seen.isoformat() if w.last_seen else None
            }
            for w in workers
        ])

    @app.route("/api/jobs/<int:job_id>/logs", methods=["GET"])
    def get_job_logs(job_id):
        job = Job.query.get_or_404(job_id)
        logs = JobLog.query.filter_by(job_id=job.id).order_by(JobLog.ts.asc()).all()
        return jsonify([
            {
                "id": log.id,
                "job_id": log.job_id,
                "message": log.message,
                "level": log.level,
                "ts": log.ts.isoformat()
            }
            for log in logs
        ])


    @app.route("/api/jobs/pending", methods=["GET"])
    def pending_jobs():
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token != app.config["WORKER_SHARED_TOKEN"]:
            return jsonify({"error":"unauthorized"}), 401
        jobs = Job.query.filter(Job.status == "pending").order_by(Job.created_at.asc()).all()
        return jsonify([{"id": j.id, "name": j.name, "bundle_filename": j.bundle_filename, "main_entry": j.main_entry, "requirements_file": j.requirements_file, "docker_image_tag": j.docker_image_tag} for j in jobs])

    # -------- Socket.IO --------
    @socketio.on("join_job")
    def on_join_job(data):
        job_id = data.get("job_id")
        join_room(f"job_{job_id}")
        emit("joined", {"room": f"job_{job_id}"})

    def append_log(job_id, message, level="INFO"):
        entry = JobLog(job_id=job_id, message=message, level=level)
        db.session.add(entry)
        db.session.commit()

    @app.template_filter("fmt_ts")
    def fmt_ts(ts):
        return ts.strftime("%Y-%m-%d %H:%M:%S")

    return app, socketio

if __name__ == "__main__":
    app, socketio = create_app()
    # eventlet is required for Flask-SocketIO default async
    socketio.run(app ,host="10.50.48.56",port=5000, debug=True)
