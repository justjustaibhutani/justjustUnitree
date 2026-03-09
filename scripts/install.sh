#!/bin/bash
# First-time setup on Go2 Jetson Orin NX
# Run this once after deploying

set -e

echo "=== JJAI Go2 First-Time Setup ==="

# System packages
sudo apt-get update
sudo apt-get install -y python3-pip portaudio19-dev

# Create data directories
mkdir -p /home/ubuntu/justjustUnitree/data/{maps,event_logs,memory}

# Install Python package
cd /home/ubuntu/justjustUnitree
pip3 install -e .

# Install with audio support
pip3 install "go2-webrtc-connect[audio,video]"

# Create systemd service
sudo tee /etc/systemd/system/jjai-go2.service > /dev/null << 'EOF'
[Unit]
Description=JJAI Go2 Robot OS
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/justjustUnitree
EnvironmentFile=/home/ubuntu/unitree_keys.env
ExecStart=/usr/bin/python3 -m jjai_go2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable jjai-go2

echo ""
echo "=== Setup complete ==="
echo "Copy unitree_keys.env.template to ~/unitree_keys.env and fill in API keys"
echo "Then: sudo systemctl start jjai-go2"
