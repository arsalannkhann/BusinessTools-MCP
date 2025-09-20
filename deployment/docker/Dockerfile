# Sales MCP Server Docker Configuration - Production Ready
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for production
RUN mkdir -p /app/credentials /app/tokens /app/logs /app/backups

# Create non-root user with proper permissions
RUN useradd -m -u 1000 salesuser && \
    chown -R salesuser:salesuser /app && \
    chmod +x /app/start_production.sh
USER salesuser

# Expose port
EXPOSE 8000

# Health check using our custom health check script
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python health_check.py || exit 1

# Environment variables for production
ENV ENVIRONMENT=production
ENV GOOGLE_CREDENTIALS_PATH=/app/credentials/google_credentials.json
ENV GOOGLE_TOKEN_PATH=/app/tokens/google_token.json
ENV GOOGLE_REFRESH_INTERVAL=1800
ENV GOOGLE_MIN_TOKEN_LIFETIME=300

# Use production startup script
CMD ["./start_production.sh"]