# Use Python 3.11 slim base image for a lightweight container
FROM python:3.11-slim

# Install system dependencies required for GIS and PostgreSQL
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*  # Clean up to reduce image size

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn  # Install gunicorn for production WSGI server

# Copy the entire project
COPY . .

# Create directories for static and media files
RUN mkdir -p staticfiles media

# Set Django settings module
ENV DJANGO_SETTINGS_MODULE=accesswash_platform.settings

# Collect static files during build
RUN python manage.py collectstatic --noinput

# Run migrations and start gunicorn, binding to Railway's dynamic PORT
CMD ["sh", "-c", "python manage.py migrate && gunicorn --bind 0.0.0.0:$PORT accesswash_platform.wsgi:application"]