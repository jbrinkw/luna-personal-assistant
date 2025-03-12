FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and git for cloning
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy local code into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port your API runs on
EXPOSE 8000

# Remove --reload flag for production and bind to 0.0.0.0
CMD ["uvicorn", "app.api.api:app", "--host", "0.0.0.0", "--port", "8000"]