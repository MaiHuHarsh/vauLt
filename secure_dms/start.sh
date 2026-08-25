#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

source venv/bin/activate
echo "Installing dependencies (first run only takes a minute)..."
pip install -q -r requirements.txt

echo ""
echo "Starting backend on http://localhost:8000 ..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

cleanup() {
  echo "Shutting down backend..."
  kill $BACKEND_PID 2>/dev/null
}
trap cleanup EXIT

sleep 3
echo "Starting frontend on http://localhost:8501 ..."
cd frontend
streamlit run app.py --server.port 8501
