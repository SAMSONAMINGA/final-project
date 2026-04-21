#!/bin/bash

# FloodGuard KE Backend - Local Development Setup

set -e

echo "============================================"
echo "FloodGuard KE Backend - Setup Script"
echo "============================================"

# Check Python version
python_version=$(python3 --version | cut -d' ' -f2)
echo "✓ Python $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Copy .env if not exists
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "⚠ Edit .env with your API keys"
fi

# Ensure PostgreSQL + PostGIS running (via docker-compose)
echo "Starting Docker services (PostgreSQL, Redis, Celery)..."
docker-compose up -d postgres redis celery celery-beat

# Wait for database
echo "Waiting for PostgreSQL..."
until docker-compose exec -T postgres pg_isready -U floodguard > /dev/null 2>&1; do
    sleep 1
done

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Populate synthetic data
echo "Populating synthetic Kenya county data..."
python tests/test_synthetic_data.py

# Start FastAPI server
echo "============================================"
echo "✓ Setup complete!"
echo "============================================"
echo ""
echo "Starting FastAPI server on http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo "Health check: curl http://localhost:8000/health"
echo ""
echo "Stop with: Ctrl+C"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
