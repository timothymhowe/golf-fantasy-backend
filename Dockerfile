# Use Python 3.10.13 slim image
FROM python:3.10.13-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY src/api/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY src/api/ .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=5001
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# Create a non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Run with Gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 run:app