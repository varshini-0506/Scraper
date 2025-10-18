#!/bin/bash
# Install Playwright browsers
playwright install chromium
playwright install-deps

# Start the application
uvicorn app.main:app --host 0.0.0.0 --port $PORT
