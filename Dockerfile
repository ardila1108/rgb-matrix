FROM python:3.11-slim-bookworm

# WITH_HARDWARE=1 builds hzeller's rpi-rgb-led-matrix Python bindings (Pi image).
# The PC/simulator image skips it.
ARG WITH_HARDWARE=0
ARG RGBMATRIX_REF=14464b3ad8974665f75a3c82355cf872311fec21
# Must match Pillow in requirements.txt (the bindings read Pillow's C structs).
ARG PILLOW_REF=11.3.0

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN if [ "$WITH_HARDWARE" = "1" ]; then \
      set -eux; \
      apt-get update; \
      apt-get install -y --no-install-recommends build-essential git; \
      rm -rf /var/lib/apt/lists/*; \
      git clone --depth 1 --branch "$PILLOW_REF" https://github.com/python-pillow/Pillow.git /tmp/pillow; \
      git clone https://github.com/hzeller/rpi-rgb-led-matrix.git /tmp/rgbmatrix; \
      git -C /tmp/rgbmatrix checkout "$RGBMATRIX_REF"; \
      CPATH=/tmp/pillow/src/libImaging pip install --no-cache-dir /tmp/rgbmatrix; \
      rm -rf /tmp/pillow /tmp/rgbmatrix; \
    fi

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .
CMD ["python", "run.py"]
