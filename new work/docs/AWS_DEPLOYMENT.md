# AURIX - AWS EC2 Deployment Guide

**Target Environment:** AWS EC2 `t2.micro` or `t3.micro` (Ubuntu 22.04 LTS)
**Constraints:** 1GB RAM (Requires Swap File to prevent Docker crashes)

## Step 1: Provision the Server
1. Log into AWS Console -> EC2 -> **Launch Instance**.
2. **Name:** `aurix-ai-engine`
3. **AMI:** Ubuntu Server 22.04 LTS (Free Tier Eligible)
4. **Instance Type:** `t2.micro` or `t3.micro`
5. **Key Pair:** Create a new `.pem` key pair and download it.
6. **Network Settings:** Allow SSH traffic from anywhere.
7. Click **Launch**.

## Step 2: Connect to the Server
Open your local terminal (PowerShell/Bash) where you downloaded your `.pem` key:
```bash
# Set permissions on Mac/Linux (Skip on Windows)
chmod 400 your-key.pem

# SSH into the instance
ssh -i "your-key.pem" ubuntu@<YOUR_EC2_PUBLIC_IP>
```

## Step 3: Prevent Crashes (The Swap File Hack)
Because the Free Tier only has 1GB of RAM, running multiple Docker containers will crash the server. Run these exact commands to allocate 4GB of your SSD as "Virtual RAM":
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make the swap file permanent across reboots
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Step 4: Install Docker
Install the Docker daemon and Docker Compose:
```bash
sudo apt update
sudo apt install docker.io docker-compose-v2 git -y

# Grant your user permission to run Docker without sudo
sudo usermod -aG docker $USER

# CRITICAL: You must disconnect from the server and SSH back in for permissions to apply!
exit
```

## Step 5: Deploy the AI Engine
SSH back into the server, clone your repository, and set up the environment variables:
```bash
# Clone the repository
git clone <YOUR_GITHUB_REPO_URL>
cd <YOUR_REPO_NAME>/new\ work

# Set up the environment variables
cp .env.example .env
nano .env
```

**Inside the `.env` file, you MUST set:**
1. Your real `GROQ_API_KEY` (and `OPENAI_API_KEY` if used).
2. The `HOST_WORKSPACE_DIR` to the absolute path of the EC2 server: 
   `HOST_WORKSPACE_DIR="/home/ubuntu/<YOUR_REPO_NAME>/new work/workspace"`

## Step 6: Build and Run
```bash
# Build the container (this may take a few minutes on a micro instance)
docker compose build

# Launch the engine in the background
docker compose up -d

# View the live logs to ensure it is running
docker logs -f aurix_ai_worker
```

Your AI Engine is now deployed 24/7 on AWS! To run a manual test scan from the server terminal:
`docker exec aurix_ai_worker python aurix_worker.py https://github.com/stamparm/DSVW`
