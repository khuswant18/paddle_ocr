#!/bin/bash
# Start the Flask backend server

cd "$(dirname "$0")"

echo "🚀 Starting Flask Backend Server..."
echo "📍 Working directory: $(pwd)"
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check if Flask is installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "❌ Flask not installed. Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "Starting server on http://localhost:5000"
echo "Press CTRL+C to stop"
echo ""

# Run the Flask app
python3 backend/app.py
