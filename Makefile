# Load variables from .env file (ignoring errors if it doesn't exist yet)
-include .env
export

# Default image name
IMAGE_NAME = rgb-matrix-app
PORT = 8000

# Check the MATRIX_ENV variable loaded from .env
ifeq ($(MATRIX_ENV),physical)
    # Physical mode (Raspberry Pi) requires sudo and hardware access privileges
    RUN_CMD = sudo docker run --privileged -p $(PORT):8000 -v $(CURDIR):/app --env-file .env -it --rm $(IMAGE_NAME)
else
    # Virtual mode (Local PC) just runs standard docker
    RUN_CMD = docker run -p $(PORT):8000 -v "$(CURDIR):/app" --env-file .env -it --rm $(IMAGE_NAME)
endif

.PHONY: help build run clean

help:
	@echo "Available commands:"
	@echo "  make build  - Build the Docker image"
	@echo "  make run    - Run the Docker container (automatically uses sudo/privileged on Pi based on .env)"
	@echo "  make clean  - Remove the Docker image"

build:
	docker build -t $(IMAGE_NAME) .

run:
	@echo "Running in $(MATRIX_ENV) mode..."
	$(RUN_CMD)

clean:
	docker rmi $(IMAGE_NAME)
