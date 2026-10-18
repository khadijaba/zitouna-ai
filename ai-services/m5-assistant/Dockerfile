FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    MODEL_DIR=/models/m5_ensemble \
    HF_HUB_OFFLINE=1 \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app
COPY requirements.txt .
# requirements.txt points pip to the CPU-only torch wheels
RUN pip install -r requirements.txt

COPY app ./app

EXPOSE 8000
# The ensemble (1 GB) is mounted at /models, not baked into the image. Loading takes ~10-20 s.
HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ[\"PORT\"]}/health')"
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
