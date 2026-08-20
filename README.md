# Oman ID Card OCR Application

This is a Flask-based web application that uses PaddleOCR to extract information from Oman ID cards and resident cards.

## Features

- Extract information from Oman ID cards and resident cards
- Extract Civil Number, Expiry Date, Date of Birth, and Signature status
- Real-time OCR processing with confidence scores
- Modern drag-and-drop interface
- REST API endpoint for integration

## Prerequisites

- Python 3.11, 3.12, 3.13, or **3.14** (3.14 recommended)
- pip (Python package installer)
- Git (for cloning the repository)

> **Why not PaddlePaddle directly?** Official `paddlepaddle` wheels currently stop at CPython 3.13 (`cp313`). There are no `cp314` wheels, so this app runs PP-OCRv5 through [onnxocr](https://pypi.org/project/onnxocr/) and ONNX Runtime, which do support Python 3.14. The OCR result format stays compatible with PaddleOCR 2.x.

## Step-by-Step Installation Guide

### 1. Clone the Repository
```bash
git clone <repository-url>
cd <repository-name>
```

### 2. Create and Activate Virtual Environment
```bash
# Create virtual environment (use the 3.14 interpreter)
python3.14 -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create Required Directories
```bash
# Create uploads directory (if not exists)
mkdir uploads
```

### 5. Running the Application

#### Development Mode
```bash
FLASK_DEBUG=1 python app.py
```
The application will be available at `http://localhost:5000`

#### Production Mode (Using Gunicorn)
```bash
gunicorn --bind 0.0.0.0:5000 --workers 1 --timeout 120 app:app
```

### 6. Setting Up as a Service (Linux)

1. Create a systemd service file:
```bash
sudo nano /etc/systemd/system/oman-ocr.service
```

2. Add the following content:
```ini
[Unit]
Description=Oman ID Card OCR Service
After=network.target

[Service]
User=<your-username>
WorkingDirectory=/path/to/your/app
Environment="PATH=/path/to/your/app/venv/bin"
ExecStart=/path/to/your/app/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 1 --timeout 120 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:
```bash
sudo systemctl enable oman-ocr
sudo systemctl start oman-ocr
```

### 7. Setting Up Nginx (Optional but Recommended)

1. Install Nginx:
```bash
sudo apt-get update
sudo apt-get install nginx
```

2. Create Nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/oman-ocr
```

3. Add the following configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

4. Enable the site and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/oman-ocr /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

## Docker Instructions

### Build the Docker Image

To build the Docker image, run the following command in the root directory of the project:

```bash
docker build -t paddleocr-app .
```

### Run the Docker Container

To run the Docker container, use the following command:

```bash
docker run -d -p 5000:5000 --name paddleocr-container paddleocr-app
```

This will start the container in detached mode and map port 5000 from the container to port 5000 on your host machine.

### Access the Application

Once the container is running, you can access the application at:

```
http://localhost:5000
```

### Check Container Logs

To check the logs of the running container, use the following command:

```bash
docker logs paddleocr-container
```

### Stop and Remove the Container

To stop and remove the container, use the following commands:

```bash
docker stop paddleocr-container
docker rm paddleocr-container
```

## Additional Information

- Docker runs Python 3.14 with Gunicorn (one worker; the OCR model is loaded per process).
- Local `python app.py` binds to `0.0.0.0` and reads `FLASK_DEBUG` / `PORT`.
- The image includes OpenCV, ONNX Runtime, and PP-OCRv5 models via onnxocr.



