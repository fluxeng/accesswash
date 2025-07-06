FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy project
COPY . .

# Create directories for static/media files
RUN mkdir -p staticfiles media

# Set environment variable for Django settings
ENV DJANGO_SETTINGS_MODULE=accesswash_platform.settings

EXPOSE 8000

# Use a simple start command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]