# DTrain Backend

A distributed machine learning training platform that allows you to submit training jobs and execute them on worker nodes. The system provides a web interface for job management and a worker agent for executing training tasks.

## 🏗 Architecture

The DTrain Backend consists of three main components:

- *Server*: Flask-based web application with job management, worker monitoring, and real-time updates
- *Worker*: Python agent that polls for jobs, downloads training bundles, and executes training tasks
- *Web UI*: Real-time dashboard for monitoring jobs, workers, and training progress

## 🚀 Features

- *Job Management*: Upload training job bundles as ZIP files
- *Worker Pool*: Scale training across multiple worker nodes
- *Real-time Monitoring*: Live updates on job progress and worker status
- *Docker Support*: Optional containerized execution for training jobs
- *System Metrics*: Monitor CPU, memory, and disk usage on workers
- *Interactive Job Acceptance*: Workers can choose which jobs to accept

## 📋 Prerequisites

- Python 3.8+
- Docker (optional, for containerized execution)
- Git

## 🛠 Installation

### 1. Clone the Repository

bash
git clone <your-repo-url>
cd DTrain-back


### 2. Server Setup

bash
cd server
pip install -r requirements.txt


### 3. Worker Setup

bash
cd ../worker
pip install -r requirements.txt


## ⚙ Configuration

### Server Configuration

Create environment variables or modify server/config.py:

bash
export SECRET_KEY="your-secret-key"
export DATABASE_URL="sqlite:///app.db"
export WORKER_SHARED_TOKEN="your-worker-token"
export UPLOAD_FOLDER="/path/to/uploads"
export JOB_BUNDLES_FOLDER="/path/to/job-bundles"


### Worker Configuration

Create worker/config.json:

json
{
    "server_url": "http://localhost:5000",
    "token": "your-worker-token",
    "worker_name": "worker-1",
    "poll_interval": 10,
    "max_concurrent_jobs": 1
}


## 🚀 Usage

### Starting the Server

bash
cd server
python app.py


The server will start on http://localhost:5000 with:
- *Dashboard*: / - View all jobs
- *Worker Monitor*: /workers - Monitor worker status
- *Job Details*: /jobs/<id> - View specific job progress

### Starting a Worker

bash
cd worker
python agent.py


The worker will:
1. Connect to the server using the configured token
2. Poll for available jobs every 10 seconds (configurable)
3. Display job details and ask for acceptance
4. Download and execute accepted jobs
5. Report progress back to the server

## 📦 Creating Training Jobs

### Job Bundle Structure

Create a ZIP file containing your training code:


my_training_job.zip
├── main.py              # Main training script (required)
├── requirements.txt     # Python dependencies (optional)
├── data/               # Training data (optional)
├── models/             # Model files (optional)
└── config.yaml         # Configuration (optional)


### Example Training Job

python
# main.py
import time
import json

def main():
    print("Starting training job...")
    
    # Training loop
    for epoch in range(1, 6):
        print(f"Epoch {epoch}/5: training...")
        time.sleep(1)
        
        # Simulate training metrics
        loss = (6 - epoch) / 5
        accuracy = epoch / 5
        
        print(f"Epoch {epoch}: loss={loss:.3f}, acc={accuracy:.3f}")
        
        # Report progress (optional)
        progress = {
            "epoch": epoch,
            "loss": loss,
            "accuracy": accuracy
        }
        print(f"PROGRESS: {json.dumps(progress)}")
    
    print("Training complete!")

if __name__ == "__main__":
    main()


### Submitting Jobs

1. *Via Web UI*: Navigate to the dashboard and use the upload form
2. *Via API*: POST to /api/jobs with multipart form data

bash
curl -X POST http://localhost:5000/api/jobs \
  -F "name=My Training Job" \
  -F "main_entry=main.py" \
  -F "requirements_file=requirements.txt" \
  -F "file=@my_training_job.zip"


## 🔧 Worker Configuration Options

### Advanced Worker Settings

json
{
    "server_url": "http://localhost:5000",
    "token": "your-worker-token",
    "worker_name": "worker-1",
    "poll_interval": 10,
    "max_concurrent_jobs": 1,
    "auto_accept_jobs": false,
    "docker_enabled": true,
    "docker_image_tag": "python:3.9-slim",
    "max_memory_gb": 8,
    "max_cpu_percent": 80
}


### Worker Environment Variables

bash
export DTRAIN_SERVER_URL="http://localhost:5000"
export DTRAIN_WORKER_TOKEN="your-token"
export DTRAIN_WORKER_NAME="worker-1"
export DTRAIN_POLL_INTERVAL="10"
export DTRAIN_MAX_JOBS="1"


## 📊 Monitoring and Logs

### Real-time Job Monitoring

- *Web Dashboard*: View all jobs and their status
- *Job Details*: Real-time logs and progress updates
- *Worker Status*: Monitor worker health and resource usage

### Job Status Types

- pending: Job uploaded, waiting for worker
- running: Job being executed by worker
- completed: Job finished successfully
- failed: Job encountered an error
- cancelled: Job was cancelled

### Log Levels

- INFO: General information and progress
- WARNING: Non-critical issues
- ERROR: Errors that may affect execution
- PROGRESS: Training metrics and progress updates

## 🐳 Docker Support

### Containerized Execution

Workers can execute jobs in Docker containers for isolation:

json
{
    "docker_enabled": true,
    "docker_image_tag": "python:3.9-slim",
    "docker_volumes": ["/host/data:/container/data"],
    "docker_environment": ["CUDA_VISIBLE_DEVICES=0"]
}


### Custom Docker Images

Create a Dockerfile in your job bundle:

dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]


## 🔒 Security Considerations

- *Token-based Authentication*: Workers authenticate using shared tokens
- *Job Isolation*: Each job runs in its own environment
- *File Validation*: Only ZIP files are accepted for job bundles
- *Resource Limits*: Configurable CPU and memory limits per worker

## 🚨 Troubleshooting

### Common Issues

1. *Worker Connection Failed*
   - Check server URL and token in config.json
   - Verify server is running and accessible

2. *Job Execution Fails*
   - Check main.py exists in job bundle
   - Verify all dependencies in requirements.txt
   - Check worker logs for specific error messages

3. *Docker Issues*
   - Ensure Docker daemon is running
   - Check Docker permissions for the worker user
   - Verify Docker image exists or can be pulled

### Debug Mode

Enable verbose logging in worker:

bash
export DTRAIN_DEBUG=true
python agent.py


## 📈 Scaling

### Multiple Workers

Run multiple worker instances on different machines:

bash
# Worker 1
export DTRAIN_WORKER_NAME="worker-1"
python agent.py

# Worker 2 (in another terminal/machine)
export DTRAIN_WORKER_NAME="worker-2"
python agent.py


### Load Balancing

- Workers automatically poll for available jobs
- Jobs are distributed based on worker availability
- No manual load balancing required

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section above
- Review worker logs for detailed error information

---

*Happy Training! 🚀*
