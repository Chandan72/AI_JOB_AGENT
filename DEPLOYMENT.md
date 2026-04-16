# Deployment Guide — AI Job Agent on AWS EC2

This guide walks you through deploying the AI Job Agent to a production
AWS EC2 instance using Docker and Docker Compose. Every step is explained
so you understand *why* each command exists, not just *what* it does.

---

## Table of Contents

1. [How the Deployment Works (Big Picture)](#1-how-the-deployment-works)
2. [Prerequisites](#2-prerequisites)
3. [Step 1 — Test Locally with Docker](#3-step-1--test-locally-with-docker)
4. [Step 2 — Push Image to Docker Hub](#4-step-2--push-image-to-docker-hub)
5. [Step 3 — Launch an EC2 Instance](#5-step-3--launch-an-ec2-instance)
6. [Step 4 — Install Docker on EC2](#6-step-4--install-docker-on-ec2)
7. [Step 5 — Deploy on EC2](#7-step-5--deploy-on-ec2)
8. [Step 6 — Upload Your Profile Data](#8-step-6--upload-your-profile-data)
9. [Updating the App (New Code)](#9-updating-the-app)
10. [Environment Variable Reference](#10-environment-variable-reference)
11. [Useful Docker Commands](#11-useful-docker-commands)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. How the Deployment Works

```
Your PC                    Docker Hub                 AWS EC2
--------                   ----------                 --------
project code               (image registry)           (cloud server)
    |                           |                         |
    |-- docker build --------->|                         |
    |-- docker push ---------->| ai-job-agent:latest     |
    |                           |                         |
    |                           |--- docker pull -------->|
    |                           |                         |
    |                           |       docker compose up |
    |                           |       - web container   |
    |                           |       - hunter container|
    |                           |                         |
    browser ------------------------------------------------> http://EC2_IP:8000
```

**Key concepts:**

- **Docker Image** — A snapshot of your app: code + Python + all
  pip packages. Built once, runs anywhere.
- **Docker Hub** — Free cloud storage for Docker images (like
  GitHub but for containers).
- **Docker Compose** — Runs multiple containers together. We have
  two: the web server and the job hunter scheduler.
- **EC2** — A virtual machine in AWS's cloud. You SSH into it
  just like a remote computer.
- **Volumes** — Persistent storage that survives container restarts.
  Your outputs, profile data, and job tracker DB live in volumes.

---

## 2. Prerequisites

### On Your Windows PC

1. **Docker Desktop** — Download from https://www.docker.com/products/docker-desktop/
   - During install, enable "WSL 2 backend" (recommended)
   - After install, open Docker Desktop and wait for it to say "Running"
   - Verify: open PowerShell and run `docker --version`

2. **Docker Hub account** — Create free at https://hub.docker.com/signup

3. **AWS account** — Create at https://aws.amazon.com/free/
   - You need a credit card but won't be charged much (~$15/month for t3.small)

4. **A `.env` file** in your project root with all API keys filled in
   (copy from `.env.example` and fill in real values)

### What You Should Know

- Basic terminal/PowerShell usage (cd, ls, running commands)
- How to open a browser (that's it for the web UI)

---

## 3. Step 1 — Test Locally with Docker

Before deploying to AWS, always verify the app runs in Docker
on your own machine. This catches 95% of issues.

### 3.1 Build the Docker image

Open PowerShell in the project folder:

```powershell
cd C:\Users\ckmaa\AI_JOB_AGENT
docker compose build
```

**What happens:** Docker reads the `Dockerfile`, downloads Python 3.11,
installs all requirements.txt packages, and copies your code into an
image. This takes 3-10 minutes the first time (subsequent builds are
faster due to caching).

### 3.2 Start the containers

```powershell
docker compose up
```

**What happens:** Docker starts two containers:
- `web` — FastAPI server on port 8000
- `hunter` — Job hunter scheduler (waits for 10 AM daily)

You'll see logs from both containers in your terminal.

### 3.3 Verify it works

Open your browser and go to: **http://localhost:8000**

You should see the AI Job Agent web UI. Try the health endpoint:
**http://localhost:8000/health** — should return `{"status": "ok"}`.

### 3.4 Stop the containers

Press `Ctrl+C` in the terminal, then:

```powershell
docker compose down
```

**Troubleshooting build failures:**
- If `pip install` fails, check that `requirements.txt` has valid packages
- If port 8000 is already in use: `docker compose down` first, or change
  the port mapping in `docker-compose.yml` from `"8000:8000"` to `"9000:8000"`

---

## 4. Step 2 — Push Image to Docker Hub

Docker Hub is where your EC2 instance will download the image from.

### 4.1 Log in to Docker Hub

```powershell
docker login
```

Enter your Docker Hub username and password when prompted.

### 4.2 Tag the image

Replace `YOUR_DOCKERHUB_USERNAME` with your actual username:

```powershell
docker tag ai-job-agent:latest YOUR_DOCKERHUB_USERNAME/ai-job-agent:latest
```

**Why tag?** Docker Hub images follow the format `username/image-name:tag`.
The tag `latest` means "the most recent version".

### 4.3 Push to Docker Hub

```powershell
docker push YOUR_DOCKERHUB_USERNAME/ai-job-agent:latest
```

This uploads your image (~1-2 GB). Takes a few minutes on first push.

### 4.4 Verify

Go to https://hub.docker.com/ and check that your repository
`ai-job-agent` appears under your account.

---

## 5. Step 3 — Launch an EC2 Instance

### 5.1 Go to EC2 Dashboard

1. Log in to https://console.aws.amazon.com/
2. Search for "EC2" in the top search bar
3. Click "Launch Instance"

### 5.2 Configure the instance

| Setting | Value | Why |
|---------|-------|-----|
| **Name** | `ai-job-agent` | Just a label |
| **AMI** | Amazon Linux 2023 | Free tier eligible, lightweight |
| **Instance type** | `t3.small` (2 vCPU, 2 GB RAM) | sentence-transformers needs ~1 GB RAM |
| **Key pair** | Create new → name it `ai-job-agent-key` → Download `.pem` file | You need this file to SSH in |
| **Storage** | 20 GB gp3 | Docker images + model downloads need space |

### 5.3 Configure Security Group (firewall)

Under "Network settings", click "Edit" and add these rules:

| Type | Port | Source | Purpose |
|------|------|--------|---------|
| SSH | 22 | My IP | So you can SSH into the server |
| Custom TCP | 8000 | 0.0.0.0/0 | So anyone can access your web app |

**Security note:** `0.0.0.0/0` means "open to the world". For a personal
project this is fine. For a real production app, you'd put a load balancer
or Cloudflare in front.

### 5.4 Launch

Click "Launch Instance". Wait 1-2 minutes for it to start.

### 5.5 Get the public IP

1. Go to EC2 → Instances
2. Click on your instance
3. Copy the **Public IPv4 address** (e.g. `54.123.45.67`)

Save this IP — you'll use it everywhere below.

---

## 6. Step 4 — Install Docker on EC2

### 6.1 SSH into your instance

**On Windows (PowerShell):**

```powershell
ssh -i "C:\path\to\ai-job-agent-key.pem" ec2-user@YOUR_EC2_PUBLIC_IP
```

If you get a permissions error on the .pem file:
```powershell
icacls "C:\path\to\ai-job-agent-key.pem" /inheritance:r /grant:r "%USERNAME%:R"
```

**On Mac/Linux:**
```bash
chmod 400 ai-job-agent-key.pem
ssh -i ai-job-agent-key.pem ec2-user@YOUR_EC2_PUBLIC_IP
```

### 6.2 Install Docker

Run these commands one by one on the EC2 instance:

```bash
# Update system packages
sudo yum update -y

# Install Docker
sudo yum install docker -y

# Start Docker and enable it on boot
sudo systemctl start docker
sudo systemctl enable docker

# Let ec2-user run docker without sudo
sudo usermod -aG docker ec2-user

# Install Docker Compose plugin
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
```

### 6.3 Apply group changes

```bash
# Log out and back in for the docker group to take effect
exit
```

SSH back in:
```powershell
ssh -i "C:\path\to\ai-job-agent-key.pem" ec2-user@YOUR_EC2_PUBLIC_IP
```

### 6.4 Verify Docker works

```bash
docker --version
docker compose version
```

Both should print version numbers without errors.

---

## 7. Step 5 — Deploy on EC2

### 7.1 Create project directory

On the EC2 instance:

```bash
mkdir -p ~/ai-job-agent
cd ~/ai-job-agent
```

### 7.2 Copy files to EC2

You need two files on EC2: `docker-compose.yml` and `.env`.

**Option A — SCP from your PC (run in a NEW PowerShell window on your PC):**

```powershell
scp -i "C:\path\to\ai-job-agent-key.pem" ^
  C:\Users\ckmaa\AI_JOB_AGENT\docker-compose.yml ^
  C:\Users\ckmaa\AI_JOB_AGENT\.env ^
  ec2-user@YOUR_EC2_PUBLIC_IP:~/ai-job-agent/
```

**Option B — Create files directly on EC2:**

```bash
# On EC2, create the .env file
nano ~/ai-job-agent/.env
# Paste your .env contents, save with Ctrl+X, Y, Enter

# Create docker-compose.yml
nano ~/ai-job-agent/docker-compose.yml
# Paste the docker-compose.yml contents, save
```

### 7.3 Update docker-compose.yml for production

On EC2, the image should be pulled from Docker Hub instead of built
locally. Edit `docker-compose.yml` on the EC2 instance:

```bash
cd ~/ai-job-agent
nano docker-compose.yml
```

Change the `web` service — remove the `build: .` line and update
the `image:` line:

```yaml
  web:
    # build: .                                       <-- remove this line
    image: YOUR_DOCKERHUB_USERNAME/ai-job-agent:latest  # <-- change this
```

Do the same for the `hunter` service:
```yaml
  hunter:
    image: YOUR_DOCKERHUB_USERNAME/ai-job-agent:latest  # <-- change this
```

Save and exit (`Ctrl+X`, `Y`, `Enter`).

### 7.4 Pull and start

```bash
cd ~/ai-job-agent

# Pull the image from Docker Hub
docker compose pull

# Start in detached mode (runs in background)
docker compose up -d
```

### 7.5 Verify deployment

```bash
# Check both containers are running
docker compose ps

# Check logs
docker compose logs web --tail 20
docker compose logs hunter --tail 20

# Test health endpoint
curl http://localhost:8000/health
```

Now open your browser and go to:
**http://YOUR_EC2_PUBLIC_IP:8000**

You should see the AI Job Agent web UI running in the cloud.

---

## 8. Step 6 — Upload Your Profile Data

The containers use Docker volumes for persistent data. To upload
your resume PDF and profile JSON:

```bash
# Find the volume path
docker volume inspect ai-job-agent_candidate_data

# Copy files into the running container
docker compose cp ./profile.json web:/app/candidate_data/profile.json
docker compose cp ./resume.pdf web:/app/candidate_data/resume.pdf
```

Or use the web UI's onboarding page to upload directly.

---

## 9. Updating the App

When you change code and want to redeploy:

### On your PC:

```powershell
cd C:\Users\ckmaa\AI_JOB_AGENT

# Rebuild the image
docker compose build

# Tag with your Docker Hub username
docker tag ai-job-agent:latest YOUR_DOCKERHUB_USERNAME/ai-job-agent:latest

# Push to Docker Hub
docker push YOUR_DOCKERHUB_USERNAME/ai-job-agent:latest
```

### On EC2 (SSH in):

```bash
cd ~/ai-job-agent

# Pull the latest image
docker compose pull

# Restart with new image (zero-downtime if using --force-recreate)
docker compose up -d --force-recreate

# Verify
docker compose ps
```

**Total update time:** ~2-5 minutes.

---

## 10. Environment Variable Reference

These go in your `.env` file. Never commit this file to git.

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | Yes | `openrouter` or `anthropic` or `openai` |
| `LLM_MODEL` | Yes | Primary model name |
| `OPENROUTER_API_KEY` | Yes* | OpenRouter API key (*if using OpenRouter) |
| `OPENROUTER_MODEL_FAST` | No | Fast model for simple tasks |
| `OPENROUTER_MODEL_SMART` | No | Smart model for complex tasks |
| `TAVILY_API_KEY` | Yes | For company research + job scraping |
| `LANGSMITH_API_KEY` | No | For prompt tracing (optional) |
| `LANGSMITH_TRACING` | No | `true` to enable tracing |
| `LANGSMITH_PROJECT` | No | LangSmith project name |
| `GMAIL_SENDER_EMAIL` | No | Gmail address for sending emails |
| `GMAIL_APP_PASSWORD` | No | Gmail app password (not regular password) |

---

## 11. Useful Docker Commands

Run these on EC2 (or locally) in the project directory:

```bash
# See running containers
docker compose ps

# View live logs (Ctrl+C to stop watching)
docker compose logs -f

# View logs for one service
docker compose logs web --tail 50
docker compose logs hunter --tail 50

# Restart a single service
docker compose restart web

# Stop everything
docker compose down

# Stop and DELETE all data (volumes too) — DESTRUCTIVE
docker compose down -v

# Enter a running container (like SSH-ing into it)
docker compose exec web bash

# Check disk usage
docker system df

# Clean up unused images (frees disk space)
docker image prune -a
```

---

## 12. Troubleshooting

### Container won't start

```bash
# Check logs for error messages
docker compose logs web --tail 50
```

Common causes:
- Missing `.env` file or missing API keys
- Port 8000 already in use (another process)
- Out of memory (check with `free -m`)

### "Cannot connect" in browser

1. Verify the container is running: `docker compose ps`
2. Check EC2 Security Group allows port 8000 from `0.0.0.0/0`
3. Check the public IP hasn't changed (it can change on stop/start
   unless you use an Elastic IP)

### Out of memory

The `sentence-transformers` model needs ~1 GB RAM. If you're on
`t2.micro` (1 GB total), you'll run out.

Solution: upgrade to `t3.small` (2 GB) or add swap:
```bash
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```

### Image too large / slow push

The image is ~1-2 GB due to `sentence-transformers` and ML deps.
This is normal. Subsequent pushes are faster because Docker only
uploads changed layers.

### EC2 public IP changes after reboot

By default, EC2 assigns a new public IP each time you stop/start
the instance. To get a fixed IP:

1. Go to EC2 → Elastic IPs → Allocate
2. Associate it with your instance
3. This IP stays the same forever (free while instance is running)

### Containers restart in a loop

```bash
docker compose logs web --tail 100
```

Look for the error. Common causes:
- Python import error (missing dependency)
- `.env` file not found
- Port conflict
