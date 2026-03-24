#!/bin/bash
set -e

echo "=========================================="
echo "  VEDA - Visual Engine for Data Analytics"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

echo "[1/3] Installing Python dependencies..."
cd backend
pip3 install -q -r requirements.txt
cd ..

echo "[2/3] Installing Node dependencies..."
cd frontend
npm install --silent
cd ..

echo "[3/3] Starting services..."
echo ""
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:5173"
echo ""

cd backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

wait
