#!/bin/bash
set -e

cd "$(dirname "$0")"

# --------------------------------------------------
# Configuration
# --------------------------------------------------

PYTHON="python3.13"

# --------------------------------------------------
# Check Python version
# --------------------------------------------------

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "ERROR: Python 3.13 is required but was not found."
    echo ""
    echo "Install it first, then run this script again."
    echo "Example:"
    echo "  sudo apt update"
    echo "  sudo apt install python3.13 python3.13-venv"
    exit 1
fi

echo "Using $($PYTHON --version)"

# --------------------------------------------------
# Create virtual environment
# --------------------------------------------------

if [ ! -d "venv" ]; then
    echo "Creating Python 3.13 virtual environment..."
    "$PYTHON" -m venv venv
fi

# --------------------------------------------------
# Activate virtual environment
# --------------------------------------------------

source venv/bin/activate

echo "Virtual environment Python:"
python --version

# --------------------------------------------------
# Install dependencies
# --------------------------------------------------

echo ""
echo "Installing dependencies..."

python -m pip install --upgrade pip setuptools wheel

python -m pip install -r requirements.txt

# --------------------------------------------------
# Start backend
# --------------------------------------------------

echo ""
echo "Starting backend on http://localhost:8000 ..."

uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 &

BACKEND_PID=$!

# --------------------------------------------------
# Cleanup when script exits
# --------------------------------------------------

cleanup() {
    echo ""
    echo "Shutting down backend..."

    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM

# --------------------------------------------------
# Give backend time to start
# --------------------------------------------------

sleep 3

# --------------------------------------------------
# Start frontend
# --------------------------------------------------

echo ""
echo "Starting frontend on http://localhost:8501 ..."

cd frontend

streamlit run app.py --server.port 8501
