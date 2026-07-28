FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir numpy PyYAML paho-mqtt ai-edge-litert
# LiteRT is the new runtime for TensorFlow Lite and is API-compatible with
# the TensorFlow Lite Interpreter API used by YAMNetClassifier.

ENTRYPOINT ["/app/addon/run.sh"]
