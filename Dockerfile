# Python 3.14 on Debian Trixie
FROM python:3.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_APP=app.py \
    FLASK_DEBUG=0

# Trixie renamed libgl1-mesa-glx -> libgl1 and libglib2.0-0 -> libglib2.0-0t64
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0t64 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# onnxocr creates model dirs inside site-packages at import time.
# Pre-create them and give the runtime user ownership so Gunicorn
# can boot as a non-root user.
RUN python - <<'PY'
from pathlib import Path
import onnxocr

root = Path(onnxocr.__file__).resolve().parent
for rel in ("rapid_table/models", "models"):
    (root / rel).mkdir(parents=True, exist_ok=True)
print(root)
PY

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p uploads \
    && chown -R appuser:appuser /app \
    && chown -R appuser:appuser /usr/local/lib/python3.14/site-packages/onnxocr

USER appuser

EXPOSE 5000

# One worker: the OCR model is loaded once per process
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "app:app"]
