# Oman ID Card OCR Application

This is a Flask-based web application that uses PaddleOCR to extract information from Oman ID cards and resident cards.

## Features

- Extract information from Oman ID cards and resident cards
- Extract Civil Number, Expiry Date, Date of Birth, and Signature status
- Real-time OCR processing with confidence scores
- Modern drag-and-drop interface
- REST API endpoint for integration

## Prerequisites

- Python 3.7, 3.8, 3.9, or 3.10 (PaddleOCR does not support Python 3.11+)
- pip (Python package installer)
- Git (for cloning the repository)

## Step-by-Step Installation Guide

### 1. Clone the Repository
```bash
git clone <repository-url>
cd <repository-name>
```

### 2. Create and Activate Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
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
python app.py
```
The application will be available at `http://localhost:5000`

#### Production Mode (Using Gunicorn)
```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
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
ExecStart=/path/to/your/app/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
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



