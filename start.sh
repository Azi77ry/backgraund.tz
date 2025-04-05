#!/bin/bash

# Free Trial Optimized Start Script
echo "Starting background remover service on Render free tier..."

# Create required directories
mkdir -p static/uploads static/results

# Free-tier optimizations:
# 1. Use only 1 worker (no parallel processing)
# 2. Reduce timeout to 60s to prevent hanging
# 3. Disable preloading to save memory
# 4. Use sync worker type (simplest, lowest overhead)
# 5. Enable Python's memory management

export PYTHONUNBUFFERED=TRUE
export FLASK_ENV=production
export MPLCONFIGDIR=/tmp/matplotlib  # Prevent matplotlib cache issues if used

# Calculate safe memory limits (adjust based on your needs)
export REMBG_THREADS=1  # Limit rembg to single thread
export OMP_NUM_THREADS=1  # Limit OpenMP threads

echo "Starting Gunicorn with optimized free-tier settings..."
exec gunicorn --bind 0.0.0.0:$PORT \
     --workers 1 \
     --threads 1 \
     --timeout 60 \
     --worker-class sync \
     --log-level warning \
     --access-logfile - \
     --error-logfile - \
     app:app