#!/bin/bash
set -e

# Install essentials
sudo apt-get update
sudo apt-get install -y git docker.io

# Setup Docker
sudo systemctl start docker
sudo systemctl enable docker

# Deploy application
sudo git clone https://github.com/jbrinkw/luna-personal-assistant.git
cd luna-personal-assistant
sudo docker build -t luna-personal-assistant .
sudo docker run -d -p 8000:8000 --name luna luna-personal-assistant