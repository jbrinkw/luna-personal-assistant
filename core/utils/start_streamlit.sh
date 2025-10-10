#!/bin/bash
# Start Luna Streamlit Chat Interface

echo "Starting Luna Streamlit Chat Interface..."
echo ""
echo "Navigate to: http://127.0.0.1:8501"
echo ""

cd "$(dirname "$0")/../.."
streamlit run core/utils/streamlit_chat.py --server.port 8501 --server.address 127.0.0.1
