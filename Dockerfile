# 1. Back to your preferred python-slim environment
FROM python:3.11-slim

# 2. Install essential build tools plus curl to download the missing headers
RUN apt-get update && apt-get install -y \
    build-essential \
    #g++ \
    python-dev-is-python3 \
    python3-pil \
    python3-dev \
    cython3 \
    git

RUN git clone --depth 1 https://github.com/python-pillow/Pillow.git \
    && cp Pillow/src/libImaging/*.h /usr/local/include/ \
    && rm -rf Pillow

COPY . /app

WORKDIR /app

RUN pip install -r requirements.txt

# 7. Move right into the sample folder for testing
#WORKDIR /app/rpi-rgb-led-matrix/bindings/python/samples
# Open the bash terminal
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]