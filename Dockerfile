# Sales MCP Server Docker Configuration
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 salesuser && \
    chown -R salesuser:salesuser /app
USER salesuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import aiohttp; import asyncio; asyncio.run(aiohttp.ClientSession().get('http://localhost:8000/health').close())" || exit 1

# Run the application
CMD ["python", "sales_mcp_server.py"]