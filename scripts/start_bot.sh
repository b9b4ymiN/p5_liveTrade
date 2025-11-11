#!/bin/bash
# Script to start the AI Trading Bot

echo "Starting AI Trading Bot..."

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | xargs)
fi

# Start the bot
python main.py
