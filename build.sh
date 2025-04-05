#!/bin/bash
# Free-tier optimized build
pip install --no-cache-dir -r requirements.txt

# Clean up to save space
rm -rf ~/.cache/pip
find /usr -name "__pycache__" -exec rm -rf {} +