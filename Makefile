# Makefile for Stellar Network Visualization

.PHONY: help install setup run clean test lint format

help:
	@echo "Stellar Network Visualization - Available commands:"
	@echo ""
	@echo "  make install    - Install dependencies"
	@echo "  make setup      - Setup database and fetch initial data"
	@echo "  make run        - Run the web application"
	@echo "  make clean      - Clean cache and temporary files"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run code linting"
	@echo "  make format     - Format code with black"
	@echo ""

install:
	pip install -r requirements/base.txt
	@echo "✅ Dependencies installed"

setup: install
	python scripts/setup_database.py
	python scripts/fetch_initial_data.py
	@echo "✅ Setup complete"

run:
	streamlit run web/app.py

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf data/cache/*
	rm -rf .pytest_cache
	@echo "✅ Cleaned cache and temporary files"

test:
	pytest tests/ -v

lint:
	flake8 src/ web/ --max-line-length=120
	pylint src/ web/

format:
	black src/ web/ scripts/ --line-length=120
	isort src/ web/ scripts/

dev-install:
	pip install -r requirements/dev.txt
	@echo "✅ Development dependencies installed"

docker-build:
	docker build -t stellar-network-viz .

docker-run:
	docker run -p 8501:8501 stellar-network-viz
