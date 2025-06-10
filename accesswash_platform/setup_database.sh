#!/bin/bash

# PostgreSQL Database Setup Script for AccessWash Platform
# Run this script to set up your PostgreSQL database with PostGIS extension

echo "🚀 Setting up PostgreSQL database for AccessWash Platform..."

# Drop existing database and user if they exist
echo "🗑️  Dropping existing database and user..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS accesswash_db;"
sudo -u postgres psql -c "DROP USER IF EXISTS accesswash_user;"

# Create database user
echo "👤 Creating database user..."
sudo -u postgres createuser --createdb --createrole --login accesswash_user

# Set password for the user
echo "🔐 Setting user password..."
sudo -u postgres psql -c "ALTER USER accesswash_user PASSWORD 'AccessWash2024!';"

# Create the main database
echo "🗄️  Creating database..."
sudo -u postgres createdb -O accesswash_user accesswash_db

# Enable PostGIS extension
echo "🌍 Enabling PostGIS extensions..."
sudo -u postgres psql -d accesswash_db -c "CREATE EXTENSION IF NOT EXISTS postgis;"
sudo -u postgres psql -d accesswash_db -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;"
sudo -u postgres psql -d accesswash_db -c "CREATE EXTENSION IF NOT EXISTS uuid-ossp;"

# Grant necessary permissions
echo "🔑 Granting permissions..."
sudo -u postgres psql -d accesswash_db -c "GRANT ALL PRIVILEGES ON DATABASE accesswash_db TO accesswash_user;"
sudo -u postgres psql -d accesswash_db -c "GRANT ALL ON SCHEMA public TO accesswash_user;"
sudo -u postgres psql -d accesswash_db -c "GRANT CREATE ON SCHEMA public TO accesswash_user;"

echo "✅ Database setup complete!"
echo "📊 Database: accesswash_db"
echo "👤 User: accesswash_user"
echo "🗝️  Password: AccessWash2024!"
echo "🌍 PostGIS extensions enabled"

# Verify PostGIS installation
echo "🔍 Verifying PostGIS installation..."
sudo -u postgres psql -d accesswash_db -c "SELECT PostGIS_Version();"

echo ""
echo "✅ Fresh database created! You can now run:"
echo "   cp .env.example .env"
echo "   # Edit .env with database credentials"
echo "   python manage.py makemigrations"
echo "   python manage.py migrate_schemas --shared"
echo "   python setup_accesswash_data.py"