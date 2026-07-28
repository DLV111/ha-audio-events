FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir numpy PyYAML paho-mqtt
# Note: `tflite-runtime` is not available as a universal wheel for all
# Python versions and architectures (particularly newer Python like 3.12).
# To add TFLite support, either:
#  - use a base image with a Python version that has published wheels (e.g. 3.10),
#  - or install a platform-specific wheel during build using a direct URL,
#  - or install `tflite-runtime` into the Supervisor host/container separately.

ENTRYPOINT ["/app/addon/run.sh"]
