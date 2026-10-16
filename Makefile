# Load variables from .env file
-include .env
export

PORT ?= 8000

# Setup defaults for Virtual mode
COMPOSE_CMD = docker compose up --build
export COMPOSE_PRIVILEGED = false

# Override if in Physical mode (Raspberry Pi)
ifeq ($(MATRIX_ENV),physical)
    # Raspberry Pi needs hardware permissions and often sudo for Docker
    COMPOSE_CMD = sudo COMPOSE_PRIVILEGED=true docker compose up --build
    export COMPOSE_PRIVILEGED = true
endif

.PHONY: help build-all up down clean

help:
	@echo "Available commands:"
	@echo "  make up    - Start both containers (auto-detects Pi vs PC via .env)"
	@echo "  make down  - Stop the containers"
	@echo "  make clean - Stop and remove volumes"

up:
	@echo "Starting application in $(MATRIX_ENV) mode..."
	$(COMPOSE_CMD)

down:
	docker compose down

clean:
	docker compose down -v