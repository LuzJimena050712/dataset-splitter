#!/usr/bin/env bash
set -o errexit

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setting up matplotlib directory..."
mkdir -p /tmp/matplotlib
export MPLCONFIGDIR=/tmp/matplotlib

echo "Building matplotlib font cache..."
python3 << 'EOF'
import os
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
print("✓ Matplotlib font cache built successfully")
EOF

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate