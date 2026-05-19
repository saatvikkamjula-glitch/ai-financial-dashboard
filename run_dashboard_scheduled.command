#!/bin/bash

cd "$(dirname "$0")"

echo "Starting scheduled AI Financial Dashboard..."
echo "Current folder:"
pwd
echo ""

if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "No venv folder found."
fi

echo ""
echo "Running dashboard automatically with existing portfolio.csv..."
echo "y" | python3 main.py

echo ""
echo "Finished scheduled dashboard run."