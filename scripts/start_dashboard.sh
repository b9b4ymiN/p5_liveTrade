#!/bin/bash
# Script to start the Streamlit Dashboard

echo "Starting Streamlit Dashboard..."

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start dashboard
streamlit run monitoring/dashboard.py --server.port=8501
