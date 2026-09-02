FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    YOLO_CONFIG_DIR=/tmp/Ultralytics

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 600 --retries 10 --index-url https://download.pytorch.org/whl/cpu torch torchvision

RUN pip install --no-cache-dir --timeout 600 --retries 10 -r requirements.txt
COPY mcc_ai_worker ./mcc_ai_worker
COPY tests ./tests

ENTRYPOINT ["python", "-m", "mcc_ai_worker"]
