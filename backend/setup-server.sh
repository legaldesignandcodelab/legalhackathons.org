#!/bin/bash
# Run this ONCE on a fresh Hetzner Ubuntu 24.04 server as root
# Usage: bash setup-server.sh

set -e

echo "=== Installing Docker ==="
apt-get update
apt-get install -y ca-certificates curl gnupg ufw
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

echo "=== Installing Certbot ==="
apt-get install -y certbot

echo "=== Configuring Firewall ==="
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "=== Creating deploy user ==="
useradd -m -s /bin/bash deploy
usermod -aG docker deploy
mkdir -p /home/deploy/.ssh
# Paste your public SSH key below (replace the placeholder):
echo "PASTE_YOUR_PUBLIC_SSH_KEY_HERE" > /home/deploy/.ssh/authorized_keys
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh

echo "=== Creating app directory ==="
mkdir -p /app/nginx
chown -R deploy:deploy /app

echo "=== Done ==="
echo "Next steps:"
echo "1. Edit /home/deploy/.ssh/authorized_keys and paste your real SSH public key"
echo "2. Run: certbot certonly --standalone -d api.legalhackathons.org"
echo "3. SSH as deploy user and follow the deployment guide"
