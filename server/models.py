from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Worker(db.Model):
    __tablename__ = "workers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    token = db.Column(db.String(120), nullable=False)  # demo auth
    status = db.Column(db.String(32), default="idle")  # idle, busy, offline
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(32), default="pending")  # pending, accepted, running, completed, failed, canceled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    bundle_filename = db.Column(db.String(300), nullable=False)  # zip path relative to JOB_BUNDLES_FOLDER
    main_entry = db.Column(db.String(200), default="main.py")     # which file to run in the container
    requirements_file = db.Column(db.String(200), default="requirements.txt")
    accepted_by = db.Column(db.Integer, db.ForeignKey("workers.id"), nullable=True)
    docker_image_tag = db.Column(db.String(200), nullable=True)   # image tag that workers should build/use
    notes = db.Column(db.Text, nullable=True)

class JobLog(db.Model):
    __tablename__ = "job_logs"
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    ts = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(16), default="INFO")
    message = db.Column(db.Text, nullable=False)
