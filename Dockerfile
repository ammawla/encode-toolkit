FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/

# Install the package
RUN pip install --no-cache-dir .

# Run as non-root user
RUN useradd -m -r mcpuser
USER mcpuser

# The MCP server communicates via stdio
ENTRYPOINT ["encode-mcp"]
