#!/bin/sh

set -e

echo "========================================"
echo "Manufacturing Quality Investigation Agent"
echo "========================================"

echo ""
echo "Initializing database..."

python deployment/docker_initialize.py

echo ""
echo "Starting FastAPI..."

exec uvicorn \
    app.main:app \
    --host 0.0.0.0 \
    --port 8000