#!/bin/bash
# Install Caddy if not already installed

set -e

if command -v caddy &> /dev/null; then
    echo "Caddy is already installed ($(caddy version))"
    exit 0
fi

echo "Installing Caddy..."

# Install Caddy from official repository
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list

apt update
apt install caddy -y

echo "Caddy installed successfully ($(caddy version))"

