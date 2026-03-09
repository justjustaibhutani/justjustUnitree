#!/bin/bash
# Deploy justjustUnitree to Go2 Jetson
# Usage: ./deploy.sh [go2-ip]

set -e

GO2_HOST="${1:-go2}"

echo "=== Deploying JJAI Go2 to ${GO2_HOST} ==="

# Sync source (exclude data, venv, git)
rsync -avz --progress \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'data/' \
    --exclude '.venv' \
    --exclude 'venv' \
    --exclude '.eggs' \
    --exclude '*.egg-info' \
    . ${GO2_HOST}:/home/ubuntu/justjustUnitree/

# Install on robot
ssh ${GO2_HOST} "cd /home/ubuntu/justjustUnitree && pip3 install -e . 2>&1 | tail -5"

echo ""
echo "=== Deploy complete ==="
echo "Start with: ssh ${GO2_HOST} 'cd /home/ubuntu/justjustUnitree && python3 -m jjai_go2'"
echo "Dashboard:  http://${GO2_HOST}:5003/unitreego2"
