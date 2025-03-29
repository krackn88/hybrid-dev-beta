#!/bin/bash

# Load environment variables
source ~/.bashrc

# Start ngrok
ngrok http $WEBHOOK_PORT &

# Start the Flask server
python3 webhook_handler.py