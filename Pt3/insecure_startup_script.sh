#!/bin/bash
DOCKER_IMAGE="ghcr.io/isaactrost/fithealth-insecure:latest"
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg nginx

# Install Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
sudo systemctl enable docker
sudo systemctl start docker

# Create a shared directory for timing info
sudo mkdir -p /shared_timing
sudo chmod 777 /shared_timing

# Start your app container with the shared volume
sudo docker pull "$DOCKER_IMAGE"
TIME_STARTED=$(date +%s%3N)
sudo docker run -d --name fithealth -p 3000:3000 -v /shared_timing:/shared_timing "$DOCKER_IMAGE"

# Set up certs (replace with your actual method, e.g., gsutil cp)
sudo mkdir -p /etc/nginx/certs/
# Example: gsutil cp gs://your-bucket/certs/* /etc/nginx/certs/
# For demo, touch dummy files (replace this!)
# Get the VMs public IP
VM_IP=$(curl -s http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip -H "Metadata-Flavor: Google")

# Generate a self-signed cert for the VMs public IP
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
-keyout /etc/nginx/certs/server.key \
-out /etc/nginx/certs/server.crt \
-subj "/CN=$VM_IP" \
-addext "subjectAltName = IP:$VM_IP"
    # Write NGINX config for one-way TLS
    sudo tee /etc/nginx/conf.d/https-proxy.conf > /dev/null <<EOF

server {
listen 443 ssl;
server_name _;

ssl_certificate           /etc/nginx/certs/server.crt;
ssl_certificate_key       /etc/nginx/certs/server.key;

ssl_protocols             TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;

location / {
    proxy_pass         http://localhost:3000;
    proxy_set_header   Host \$host;
    proxy_set_header   X-Real-IP \$remote_addr;
    proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto \$scheme;
    proxy_connect_timeout 300;
    proxy_send_timeout 300;
    proxy_read_timeout 300;
    send_timeout 300;
}
}
EOF

sudo systemctl enable nginx
sudo systemctl restart nginx

# Wait for the container to (hopefully) write the file
sleep 10

# Try to read TIME_ENDED from the shared volume
if sudo test -f /shared_timing/time_ended.txt; then
    TIME_ENDED=$(sudo cat /shared_timing/time_ended.txt)
    echo "$TIME_STARTED" | sudo tee /time_started.txt > /dev/null
    echo "$TIME_ENDED" | sudo tee /time_ended.txt > /dev/null
    DIFF=$((TIME_ENDED - TIME_STARTED))
    echo "$DIFF" | sudo tee /time_diff.txt > /dev/null
else
    echo "ERROR: /shared_timing/time_ended.txt not found or could not be read" | sudo tee /time_error.txt > /dev/null
fi