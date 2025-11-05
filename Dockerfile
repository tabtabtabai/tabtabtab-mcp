FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server.py .
COPY __init__.py .

# Set environment variables
ENV TABTABTAB_API_KEY=""
ENV TABTABTAB_SERVER_URL="https://sheets.tabtabtab.ai"
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose the port (Cloud Run will override PORT env var)
EXPOSE 8080

# Run the MCP server
CMD ["python", "server.py"]

