# Docker Learning Guide

## Page 1: Introduction to Docker

### What is Docker? 

Docker is an open-source platform that enables developers to automate the deployment, scaling, and management of applications using containerization technology.  Containers package an application with all of its dependencies, libraries, and configuration files, ensuring that it runs consistently across different computing environments. 

### Why Use Docker?

**Key Benefits:**

1. **Consistency Across Environments**: Docker ensures your application runs the same way in development, testing, and production environments
2. **Isolation**: Each container runs in isolation, preventing conflicts between applications and their dependencies
3. **Portability**:  Containers can run on any system that supports Docker, regardless of the underlying infrastructure
4. **Resource Efficiency**: Containers share the host OS kernel, making them lighter than virtual machines
5. **Rapid Deployment**: Containers start in seconds, enabling faster development and deployment cycles
6. **Version Control**: Docker images can be versioned, making it easy to roll back to previous versions

### Docker vs Virtual Machines

| Feature | Docker Containers | Virtual Machines |
|---------|------------------|------------------|
| **Size** | Lightweight (MBs) | Heavy (GBs) |
| **Startup Time** | Seconds | Minutes |
| **Performance** | Near-native | Slower due to hypervisor |
| **Isolation** | Process-level | Complete OS isolation |
| **Resource Usage** | Shares host kernel | Requires full OS per VM |

### Core Docker Concepts

**1. Docker Image**
- A read-only template containing the application code, runtime, libraries, and dependencies
- Built using a Dockerfile
- Images are stored in registries like Docker Hub

**2. Docker Container**
- A running instance of a Docker image
- Isolated, lightweight, and executable package
- Can be started, stopped, moved, and deleted

**3. Dockerfile**
- A text file containing instructions to build a Docker image
- Defines the base image, dependencies, and commands to run

**4. Docker Registry**
- A storage and distribution system for Docker images
- Docker Hub is the default public registry
- Organizations can host private registries

**5. Docker Engine**
- The core component that builds and runs containers
- Consists of a server (daemon), REST API, and CLI

### Installing Docker

**Linux (Ubuntu/Debian):**
```bash
# Update package index
sudo apt-get update

# Install required packages
sudo apt-get install apt-transport-https ca-certificates curl software-properties-common

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

# Add Docker repository
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

# Install Docker
sudo apt-get update
sudo apt-get install docker-ce

# Verify installation
docker --version
```

**macOS:**
- Download Docker Desktop from docker.com
- Install the . dmg file
- Start Docker Desktop from Applications

**Windows:**
- Download Docker Desktop for Windows
- Enable WSL 2 if prompted
- Install and restart

### Basic Docker Commands

```bash
# Check Docker version
docker --version

# View Docker system information
docker info

# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# List Docker images
docker images

# Pull an image from Docker Hub
docker pull ubuntu:latest

# Run a container
docker run hello-world

# Stop a running container
docker stop <container-id>

# Remove a container
docker rm <container-id>

# Remove an image
docker rmi <image-id>
```

---

## Page 2: Working with Docker Images and Containers

### Understanding Docker Images

Docker images are built in layers.  Each instruction in a Dockerfile creates a new layer, and layers are cached to speed up subsequent builds.

**Image Layers:**
- Base layer:  Operating system (e.g., Ubuntu, Alpine)
- Additional layers: Dependencies, application code, configuration
- Top layer: Entry point or default command

### Creating Your First Dockerfile

A Dockerfile is a blueprint for building Docker images.  Here's a simple example:

```dockerfile
# Use an official Python runtime as base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container
COPY .  /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable
ENV NAME World

# Run app.py when the container launches
CMD ["python", "app.py"]
```

### Dockerfile Instructions

**Common Dockerfile Commands:**

1. **FROM**: Sets the base image
   ```dockerfile
   FROM ubuntu:20.04
   FROM node:16-alpine
   ```

2. **WORKDIR**: Sets the working directory
   ```dockerfile
   WORKDIR /usr/src/app
   ```

3. **COPY**:  Copies files from host to container
   ```dockerfile
   COPY package.json . 
   COPY . /app
   ```

4. **ADD**: Similar to COPY but can extract archives and download from URLs
   ```dockerfile
   ADD archive.tar.gz /app
   ```

5. **RUN**: Executes commands during build
   ```dockerfile
   RUN apt-get update && apt-get install -y curl
   RUN npm install
   ```

6. **CMD**: Provides default command to run when container starts
   ```dockerfile
   CMD ["node", "server.js"]
   ```

7. **ENTRYPOINT**:  Configures container to run as an executable
   ```dockerfile
   ENTRYPOINT ["python", "app.py"]
   ```

8. **ENV**: Sets environment variables
   ```dockerfile
   ENV NODE_ENV=production
   ENV PORT=3000
   ```

9. **EXPOSE**: Documents which ports the container listens on
   ```dockerfile
   EXPOSE 80 443
   ```

10. **VOLUME**: Creates a mount point for persistent data
    ```dockerfile
    VOLUME /data
    ```

### Building Docker Images

```bash
# Build an image from Dockerfile in current directory
docker build -t myapp: 1.0 .

# Build with a specific Dockerfile
docker build -f Dockerfile.dev -t myapp:dev .

# Build without cache
docker build --no-cache -t myapp:1.0 .

# Build with build arguments
docker build --build-arg VERSION=1.2.3 -t myapp:1.0 .
```

**Tag Format:** `repository:tag` or `registry/repository:tag`

### Running Containers

```bash
# Run a container from an image
docker run myapp:1.0

# Run in detached mode (background)
docker run -d myapp:1.0

# Run with a custom name
docker run --name my-container myapp:1.0

# Run with port mapping (host:container)
docker run -p 8080:80 myapp:1.0

# Run with environment variables
docker run -e DATABASE_URL=postgres://db myapp:1.0

# Run with volume mount
docker run -v /host/path:/container/path myapp: 1.0

# Run interactively with a shell
docker run -it ubuntu:20.04 /bin/bash

# Run and remove container after exit
docker run --rm myapp:1.0

# Run with resource limits
docker run --memory="512m" --cpus="1.5" myapp:1.0
```

### Managing Containers

```bash
# Start a stopped container
docker start <container-id>

# Stop a running container
docker stop <container-id>

# Restart a container
docker restart <container-id>

# Pause a running container
docker pause <container-id>

# Unpause a container
docker unpause <container-id>

# View container logs
docker logs <container-id>

# Follow logs in real-time
docker logs -f <container-id>

# Execute a command in a running container
docker exec <container-id> ls /app

# Open a shell in a running container
docker exec -it <container-id> /bin/bash

# Inspect container details
docker inspect <container-id>

# View container resource usage
docker stats <container-id>

# Copy files between host and container
docker cp file.txt <container-id>:/app/
docker cp <container-id>:/app/output.txt .
```

### Practical Example: Node.js Application

**app.js:**
```javascript
const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

app.get('/', (req, res) => {
  res.send('Hello Docker!');
});

app.listen(port, () => {
  console.log(`App listening on port ${port}`);
});
```

**package.json:**
```json
{
  "name": "docker-demo",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.0"
  }
}
```

**Dockerfile:**
```dockerfile
FROM node:16-alpine
WORKDIR /usr/src/app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["node", "app.js"]
```

**Build and Run:**
```bash
docker build -t node-demo: 1.0 .
docker run -p 3000:3000 node-demo:1.0
# Visit http://localhost:3000
```

---

## Page 3: Docker Compose and Multi-Container Applications

### What is Docker Compose?

Docker Compose is a tool for defining and running multi-container Docker applications. You use a YAML file to configure your application's services, networks, and volumes, then create and start all services with a single command.

**Benefits:**
- Define entire application stack in one file
- Easy management of multiple containers
- Simplified networking between services
- Environment variable management
- Volume orchestration
- Perfect for development and testing

### Docker Compose File Structure

A `docker-compose.yml` file defines services, networks, and volumes: 

```yaml
version: '3.8'

services:
  web:
    build: . 
    ports:
      - "5000:5000"
    volumes:
      - . :/code
    environment:
      - FLASK_ENV=development
    depends_on:
      - redis
  
  redis:
    image:  redis:alpine
    ports: 
      - "6379:6379"

volumes:
  data: 

networks:
  app-network:
```

### Docker Compose Commands

```bash
# Start all services defined in docker-compose.yml
docker-compose up

# Start in detached mode
docker-compose up -d

# Build images before starting
docker-compose up --build

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# View running services
docker-compose ps

# View logs
docker-compose logs

# Follow logs for a specific service
docker-compose logs -f web

# Execute command in a service
docker-compose exec web bash

# Scale a service to multiple instances
docker-compose up --scale web=3

# Restart services
docker-compose restart

# Pull latest images
docker-compose pull
```

### Complete Example: Web Application with Database

**Project Structure:**
```
my-project/
├── docker-compose. yml
├── web/
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
└── nginx/
    └── nginx.conf
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  # PostgreSQL Database
  db:
    image:  postgres:14-alpine
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - backend

  # Python Flask Application
  web:
    build: ./web
    command: python app.py
    volumes:
      - ./web:/app
    ports:
      - "5000:5000"
    environment: 
      - DATABASE_URL=postgresql://admin:secret@db:5432/myapp
      - REDIS_URL=redis://cache:6379/0
    depends_on: 
      - db
      - cache
    networks:
      - backend
      - frontend

  # Redis Cache
  cache:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - backend

  # Nginx Reverse Proxy
  nginx: 
    image: nginx:alpine
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
    depends_on: 
      - web
    networks: 
      - frontend

volumes: 
  postgres_data: 

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
```

**web/Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . . 

CMD ["python", "app.py"]
```

**web/requirements.txt:**
```
flask==2.3.0
psycopg2-binary==2.9.6
redis==4.5.5
sqlalchemy==2.0.15
```

**web/app.py:**
```python
from flask import Flask, jsonify
import psycopg2
import redis
import os

app = Flask(__name__)

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')
REDIS_URL = os.getenv('REDIS_URL')

# Redis connection
cache = redis.from_url(REDIS_URL)

@app.route('/')
def home():
    cache.incr('hits')
    hits = cache.get('hits').decode('utf-8')
    return jsonify({
        'message': 'Hello from Docker Compose!',
        'hits':  hits
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app. run(host='0.0.0.0', port=5000, debug=True)
```

### Networking in Docker Compose

**Service Discovery:**
- Services can communicate using service names as hostnames
- Example: `db` service accessible at `db:5432`
- Docker Compose creates a default network for all services

**Custom Networks:**
```yaml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No external access
```

### Volumes in Docker Compose

**Named Volumes:**
```yaml
volumes:
  db_data:
  redis_data: 

services:
  db:
    volumes:
      - db_data:/var/lib/postgresql/data
```

**Bind Mounts:**
```yaml
services:
  web:
    volumes:
      - ./code:/app  # Host directory mounted to container
      - /app/node_modules  # Anonymous volume
```

### Environment Variables

**Methods to set environment variables:**

1. **Directly in docker-compose.yml:**
```yaml
services:
  web:
    environment:
      - DEBUG=true
      - PORT=8000
```

2. **Using .env file:**
```yaml
services:
  web: 
    env_file:
      - .env
```

**. env file:**
```
DEBUG=true
DATABASE_URL=postgresql://user:pass@db/myapp
SECRET_KEY=mysecretkey
```

3. **From host environment:**
```yaml
services:
  web: 
    environment:
      - API_KEY=${API_KEY}
```

### Best Practices

1. **Use specific image versions** instead of `latest`
2. **Separate build and runtime dependencies**
3. **Use multi-stage builds** for smaller images
4. **Don't store secrets** in docker-compose. yml
5. **Use named volumes** for persistent data
6. **Implement health checks** for services
7. **Use . dockerignore** to exclude unnecessary files

**Health Check Example:**
```yaml
services:
  web:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## Page 4: Advanced Docker Concepts and Best Practices

### Multi-Stage Builds

Multi-stage builds allow you to use multiple FROM statements in a Dockerfile, creating smaller, more secure production images by separating build and runtime dependencies.

**Example: Go Application**
```dockerfile
# Build stage
FROM golang:1.20-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o main .

# Production stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates
WORKDIR /root/

# Copy only the binary from builder
COPY --from=builder /app/main .

EXPOSE 8080
CMD ["./main"]
```

**Benefits:**
- Smaller final image (only runtime dependencies)
- Improved security (fewer attack surfaces)
- Faster deployment (smaller images transfer faster)
- Separation of concerns (build vs. runtime)

**Example: Node.js Application**
```dockerfile
# Build stage
FROM node:16 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . . 
RUN npm run build

# Production stage
FROM node:16-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package*.json ./
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

### Docker Security Best Practices

**1. Use Official and Verified Images**
```dockerfile
# Good:  Official image
FROM node:16-alpine

# Avoid: Unverified images
FROM random-user/node:latest
```

**2. Run as Non-Root User**
```dockerfile
FROM node:16-alpine

# Create app user
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

WORKDIR /app
COPY --chown=appuser:appgroup .  . 

# Switch to non-root user
USER appuser

CMD ["node", "server.js"]
```

**3. Minimize Attack Surface**
```dockerfile
# Use minimal base images
FROM alpine:3.18
FROM scratch  # For compiled binaries

# Remove unnecessary packages
RUN apt-get remove -y build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
```

**4. Scan Images for Vulnerabilities**
```bash
# Using Docker Scout
docker scout cves myapp: latest

# Using Trivy
trivy image myapp:latest

# Using Snyk
snyk container test myapp:latest
```

**5. Don't Store Secrets in Images**
```dockerfile
# Bad: Hardcoded secrets
ENV API_KEY=12345

# Good: Use secrets at runtime
# Pass via environment variables or Docker secrets
```

**6. Use . dockerignore**
```
# . dockerignore
node_modules
npm-debug.log
.git
. env
.env.local
*. md
. DS_Store
coverage
. vscode
```

### Docker Networking Deep Dive

**Network Drivers:**

1. **Bridge** (default): Isolated network on a single host
2. **Host**:  Container uses host's network stack
3. **None**:  Disables networking
4. **Overlay**: Multi-host networking for Swarm
5. **Macvlan**:  Assigns MAC address to container

**Network Commands:**
```bash
# Create a network
docker network create my-network

# List networks
docker network ls

# Inspect network
docker network inspect my-network

# Connect container to network
docker network connect my-network my-container

# Disconnect container from network
docker network disconnect my-network my-container

# Remove network
docker network rm my-network
```

**Network Example:**
```bash
# Create a custom bridge network
docker network create --driver bridge app-network

# Run containers on the network
docker run -d --name db --network app-network postgres:14
docker run -d --name web --network app-network -p 80:80 nginx

# Containers can communicate using service names
# web can access db at:  db:5432
```

### Docker Volumes and Data Persistence

**Volume Types:**

1. **Named Volumes**: Managed by Docker
   ```bash
   docker volume create my-data
   docker run -v my-data:/data myapp
   ```

2. **Bind Mounts**: Host filesystem paths
   ```bash
   docker run -v /host/path:/container/path myapp
   ```

3. **tmpfs Mounts**: Memory-only (Linux)
   ```bash
   docker run --tmpfs /tmp myapp
   ```

**Volume Commands:**
```bash
# Create volume
docker volume create my-volume

# List volumes
docker volume ls

# Inspect volume
docker volume inspect my-volume

# Remove volume
docker volume rm my-volume

# Remove unused volumes
docker volume prune

# Backup volume data
docker run --rm -v my-volume:/data -v $(pwd):/backup alpine \
  tar czf /backup/backup.tar. gz /data

# Restore volume data
docker run --rm -v my-volume:/data -v $(pwd):/backup alpine \
  tar xzf /backup/backup.tar.gz -C /
```

### Optimizing Docker Images

**1. Use Appropriate Base Images**
```dockerfile
# Size comparison
FROM ubuntu:20.04      # ~77MB
FROM debian:11-slim    # ~80MB
FROM alpine:3.18       # ~7MB
FROM scratch           # ~0MB (for static binaries)
```

**2.  Combine RUN Commands**
```dockerfile
# Bad: Multiple layers
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y git

# Good: Single layer
RUN apt-get update && \
    apt-get install -y curl git && \
    rm -rf /var/lib/apt/lists/*
```

**3. Order Instructions by Change Frequency**
```dockerfile
FROM node:16-alpine

WORKDIR /app

# Dependencies change less frequently
COPY package*.json ./
RUN npm ci --only=production

# Source code changes more frequently
COPY .  .

CMD ["node", "server.js"]
```

**4. Use .dockerignore**
Exclude unnecessary files to reduce build context size.

**5. Leverage Build Cache**
```bash
# Build with cache
docker build -t myapp:1.0 .

# Build without cache
docker build --no-cache -t myapp:1.0 .

# Use BuildKit for better caching
DOCKER_BUILDKIT=1 docker build -t myapp:1.0 .
```

### Container Orchestration Introduction

**Docker Swarm:**
- Native Docker clustering and orchestration
- Simple to set up and use
- Good for small to medium deployments

```bash
# Initialize Swarm
docker swarm init

# Deploy a stack
docker stack deploy -c docker-compose.yml myapp

# List services
docker service ls

# Scale a service
docker service scale myapp_web=5
```

**Kubernetes:**
- Industry-standard container orchestration
- Advanced features and ecosystem
- Better for large, complex deployments
- Steep learning curve

**When to Use What:**
- **Single host**: Docker Compose
- **Small cluster**: Docker Swarm
- **Large scale, complex**: Kubernetes

### Monitoring and Logging

**Container Stats:**
```bash
# Real-time stats
docker stats

# Stats for specific container
docker stats my-container

# Export stats
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

**Logging:**
```bash
# View logs
docker logs my-container

# Follow logs
docker logs -f my-container

# Last 100 lines
docker logs --tail 100 my-container

# Logs since timestamp
docker logs --since 2025-12-29T10:00:00 my-container
```

**Logging Drivers:**
```bash
# Configure logging driver
docker run --log-driver=json-file --log-opt max-size=10m my-container
```

### Debugging Containers

```bash
# Inspect container
docker inspect my-container

# View processes
docker top my-container

# Execute commands
docker exec my-container ps aux

# Access shell
docker exec -it my-container /bin/sh

# View filesystem changes
docker diff my-container

# Export container filesystem
docker export my-container > container. tar

# Check events
docker events
```

### Docker Command Cheat Sheet

```bash
# Images
docker build -t name:tag . 
docker pull image:tag
docker push image:tag
docker images
docker rmi image-id

# Containers
docker run -d -p 80:80 image
docker ps
docker stop container-id
docker rm container-id
docker exec -it container-id bash

# Cleanup
docker system prune
docker container prune
docker image prune
docker volume prune
docker network prune

# System
docker info
docker version
docker system df
```

### Next Steps

**Further Learning:**
1. **Kubernetes**:  Learn container orchestration at scale
2. **CI/CD Integration**: Integrate Docker into pipelines (GitHub Actions, GitLab CI)
3. **Docker Security**: Advanced security scanning and hardening
4. **Microservices**: Build distributed systems with Docker
5. **Cloud Platforms**: Deploy on AWS ECS, Google Cloud Run, Azure Container Instances

**Resources:**
- Official Docker Documentation: docs.docker.com
- Docker Hub: hub.docker.com
- Play with Docker: labs.play-with-docker.com
- Docker Samples: github.com/docker/awesome-compose

**Practice Projects:**
1. Containerize an existing application
2. Build a multi-service application with Docker Compose
3. Create a CI/CD pipeline with Docker
4. Implement blue-green deployment with containers
5. Set up monitoring and logging for containers

---

**End of Docker Learning Guide**