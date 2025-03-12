#!/bin/bash

# Update system
sudo yum update -y

# Install Docker
sudo yum install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user

# Clone the repository
git clone https://github.com/your-username/luna-personal-assistant.git
cd luna-personal-assistant

# Build and run Docker container
sudo docker build -t luna-personal-assistant .
sudo docker run -d -p 80:8000 luna-personal-assistant