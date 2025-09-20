# 🚀 Deployment Guide

This folder contains all deployment configurations and scripts for the Sales MCP Server.

## 📁 Directory Structure

```
deployment/
├── setup_aws.sh                    # Environment setup and dependency installation
├── test_local.py                   # Local testing before deployment  
├── start_production.sh             # Production startup script
├── .env.production                 # Production environment template
├──
├── aws/                            # AWS deployment files
│   ├── deploy.sh                   # Automated AWS deployment script
│   ├── cloudformation-template.yml # Complete AWS infrastructure
│   ├── ecs-task-definition.json    # ECS task configuration
│   └── start_multiservice.sh       # Multi-service container startup
│
└── docker/                        # Docker configurations
    ├── Dockerfile                  # Production container
    ├── Dockerfile.multiservice     # Multi-service container
    ├── docker-compose.prod.yml     # Production docker-compose
    └── k8s-deployment.yml          # Kubernetes deployment
```

## 🚀 Quick Deployment

### 1. Local Testing
```bash
# Setup environment
./deployment/setup_aws.sh

# Test locally
./deployment/test_local.py
```

### 2. AWS Deployment
```bash
# Configure deployment settings
vim deployment/aws/deploy.sh

# Deploy to AWS
./deployment/aws/deploy.sh
```

## 🔧 Configuration Files

- **`.env.production`** - Production environment variables template
- **`cloudformation-template.yml`** - Complete AWS infrastructure as code
- **`ecs-task-definition.json`** - ECS Fargate task configuration
- **`docker-compose.prod.yml`** - Multi-container production setup
- **`k8s-deployment.yml`** - Kubernetes deployment configuration

## 🎯 Deployment Targets

1. **Local Development** - Docker Compose
2. **AWS ECS Fargate** - Production cloud deployment  
3. **Kubernetes** - Enterprise container orchestration
4. **Docker Swarm** - Alternative orchestration

## 📊 Architecture

- **MCP Server**: Port 8000 (API endpoints)
- **Voice Interface**: Port 8001 (Web UI + WebSocket)
- **Load Balancer**: HTTPS termination and routing
- **Auto-scaling**: 2-10 instances based on load
- **Persistent Storage**: EFS for tokens and logs

## 🔐 Security

- OAuth token auto-refresh every 30 minutes
- AWS Secrets Manager for API keys
- Encrypted storage and transit
- Private subnets for containers
- Security groups with minimal access

## 💰 Cost Optimization

- Fargate Spot instances for 70% savings
- Auto-scaling based on CPU/memory
- EFS storage for persistent data
- CloudWatch for monitoring and alerting

Ready to deploy! 🚀
