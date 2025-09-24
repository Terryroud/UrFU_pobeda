# Use a stable Python base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy only requirements first (for better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose the service port 
EXPOSE 8003

# Run FastAPI app with uvicorn
CMD ["uvicorn", "bot_main:app", "--host", "0.0.0.0", "--port", "8003"]
