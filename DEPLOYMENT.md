# 🚀 Production Deployment Guide

This guide covers deploying the Sales MCP Server to production with automatic Google token refresh.

## 🎯 Production Features

- **Automatic Token Refresh**: Google OAuth tokens refresh automatically every 30 minutes
- **Health Monitoring**: Built-in health checks for all services and tokens
- **Zero-Downtime Deployment**: Graceful handling of token expiration
- **Enterprise Ready**: Docker and Kubernetes configurations included
- **Secure Credentials**: Proper secret management and volume mounting

## 📋 Prerequisites

1. **Google OAuth Setup**: Complete OAuth credentials from Google Cloud Console
2. **Initial Token**: Run OAuth flow once to get initial refresh token
3. **Production Environment**: Docker, Kubernetes, or cloud platform
4. **Domain Setup**: SSL certificate for production domain (recommended)

## 🏗️ Deployment Options

### Option 1: Docker Compose (Recommended for Small Teams)

```bash
# 1. Prepare environment
cp .env.production .env
# Edit .env with your actual credentials

# 2. Create directory structure
mkdir -p credentials token_storage backups logs

# 3. Copy your Google credentials
cp /path/to/your/google_credentials.json credentials/

# 4. Get initial token (run once)
python calendly_oauth_complete.py
cp token.json token_storage/google_token.json

# 5. Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# 6. Monitor logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Option 2: Kubernetes (Enterprise)

```bash
# 1. Create namespace
kubectl create namespace mcp-server

# 2. Create secrets
kubectl create secret generic mcp-credentials \
  --from-file=google_credentials.json=./credentials/google_credentials.json \
  --from-env-file=.env.production \
  -n mcp-server

# 3. Deploy to cluster
kubectl apply -f k8s-deployment.yml

# 4. Check deployment status
kubectl get pods -n mcp-server
kubectl logs -f deployment/mcp-server -n mcp-server
```

### Option 3: Manual Server Setup

```bash
# 1. Clone and setup
git clone <your-repo>
cd Theta-MCP
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
export ENVIRONMENT=production
export GOOGLE_CREDENTIALS_PATH=./credentials/google_credentials.json
export GOOGLE_TOKEN_PATH=./token_storage/google_token.json

# 3. Create directories and copy credentials
mkdir -p credentials token_storage logs backups
cp /path/to/your/google_credentials.json credentials/
cp token.json token_storage/google_token.json

# 4. Start with automatic refresh
./start_production.sh
```

## 🔑 Token Management

### Automatic Refresh (Production Mode)

When `ENVIRONMENT=production`, the server automatically:
- Refreshes tokens every 30 minutes (configurable)
- Monitors token expiry continuously
- Attempts refresh when <5 minutes remain
- Logs all refresh activities
- Gracefully handles refresh failures

### Manual Refresh (If Needed)

```bash
# Check token status
python health_check.py

# Manual refresh
python refresh_google_token.py

# Verify refresh worked
python health_check.py
```

### Environment Variables

```bash
# Core settings
ENVIRONMENT=production                    # Enables auto-refresh
GOOGLE_CREDENTIALS_PATH=./credentials/... # OAuth credentials
GOOGLE_TOKEN_PATH=./token_storage/...     # Token storage

# Auto-refresh tuning
GOOGLE_REFRESH_INTERVAL=1800             # 30 minutes (seconds)
GOOGLE_MIN_TOKEN_LIFETIME=300            # 5 minutes (seconds)
```

## 📊 Monitoring & Health Checks

### Built-in Health Check

```bash
# Manual health check
python health_check.py

# Returns JSON status:
{
  "status": "healthy",
  "google_token": "valid",
  "tools_configured": 13,
  "server_status": "running"
}
```

### Docker Health Check

```yaml
healthcheck:
  test: ["CMD", "python", "health_check.py"]
  interval: 60s
  timeout: 10s
  retries: 3
```

### Kubernetes Health Probes

```yaml
livenessProbe:
  exec:
    command: ["python", "health_check.py"]
  initialDelaySeconds: 30
  periodSeconds: 60
```

## 🔒 Security Best Practices

### Credential Management

1. **Never commit credentials**: Use `.gitignore` for all credential files
2. **Use environment variables**: For all sensitive configuration
3. **Volume mounting**: Mount credentials as read-only in containers
4. **Secret management**: Use Kubernetes secrets or cloud secret managers
5. **Rotate tokens**: Regular token rotation (automatic with OAuth refresh)

### Network Security

```yaml
# Docker Compose with network isolation
networks:
  mcp-network:
    driver: bridge

services:
  mcp-server:
    networks:
      - mcp-network
    ports:
      - "127.0.0.1:8000:8000"  # Bind to localhost only
```

## 🚨 Troubleshooting

### Common Issues

**Token Expired Error**
```bash
# Check token status
python health_check.py

# Manual refresh
python refresh_google_token.py

# Restart service if needed
docker-compose restart mcp-server
```

**Auto-refresh Not Working**
```bash
# Check environment
echo $ENVIRONMENT  # Should be "production"

# Check logs for refresh attempts
docker-compose logs mcp-server | grep "refresh"

# Verify credentials paths
ls -la $GOOGLE_CREDENTIALS_PATH
ls -la $GOOGLE_TOKEN_PATH
```

**Health Check Failing**
```bash
# Run health check manually
docker exec mcp-server-prod python health_check.py

# Check server logs
docker-compose logs mcp-server

# Verify all tools loading
docker exec mcp-server-prod python -c "
import asyncio
from sales_mcp_server import create_server
asyncio.run(create_server().run())
"
```

### Log Analysis

```bash
# Docker Compose logs
docker-compose -f docker-compose.prod.yml logs -f

# Kubernetes logs
kubectl logs -f deployment/mcp-server -n mcp-server

# Filter for token refresh events
docker-compose logs mcp-server | grep "Token\|refresh\|OAuth"
```

## 🔄 Maintenance

### Regular Tasks

1. **Monitor token health**: Check health endpoint regularly
2. **Log rotation**: Configure log rotation for long-running deployments
3. **Backup tokens**: Regular backup of token storage
4. **Update credentials**: Rotate API keys periodically
5. **Update dependencies**: Keep Python packages updated

### Backup Strategy

```bash
# Backup tokens and credentials
tar -czf backup-$(date +%Y%m%d).tar.gz \
  credentials/ token_storage/ .env.production

# Automated backup (add to crontab)
0 2 * * * cd /app && tar -czf backups/backup-$(date +%Y%m%d).tar.gz credentials/ token_storage/
```

## 🌐 Cloud Deployment

### AWS ECS/Fargate
- Use AWS Secrets Manager for credentials
- ECS Task Definitions with health checks
- Application Load Balancer for SSL termination

### Google Cloud Run
- Cloud Secret Manager integration
- Automatic scaling and health checks
- Cloud SQL for token persistence (optional)

### Azure Container Instances
- Azure Key Vault for secrets
- Container Groups with health probes
- Azure API Management for endpoint security

## 📈 Scaling Considerations

### High Availability
- Multiple replicas with shared token storage
- Load balancing with session affinity
- Distributed token refresh coordination

### Performance Optimization
- Connection pooling for HTTP clients
- Async operations for all API calls
- Caching for frequently accessed data

## 🎉 Success Verification

After deployment, verify everything works:

```bash
# 1. Health check passes
curl http://your-domain/health

# 2. Token is valid and auto-refreshing
python health_check.py

# 3. All tools are configured
# Check server logs for "Successfully configured X/13 tools"

# 4. Sample API call works
# Test one of your MCP tools

# 5. Auto-refresh is running
# Check logs for refresh messages every 30 minutes
```

Your Sales MCP Server is now production-ready with automatic token refresh! 🎊
