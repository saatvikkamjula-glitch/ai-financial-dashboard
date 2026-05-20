#!/bin/bash

cd "$(dirname "$0")"

echo "AI Financial Dashboard Schedule Setup"
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
echo "Opening schedule setup..."
python3 setup_scheduler.py

echo ""
echo "Schedule setup finished."
echo "You can close this window now."

read -p "Press Enter to exit..."
