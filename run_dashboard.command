#!/bin/bash

cd "$(dirname "$0")"

echo "Starting AI Financial Dashboard..."
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
echo "Checking Python..."
which python3
python3 --version

echo ""
echo "Running main.py..."
python3 main.py

echo ""
echo "Finished running dashboard."
echo "If there was an error, read the message above."

read -p "Press Enter to close this window..."