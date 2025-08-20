#!/bin/bash
set -e

echo "🚀 Starting AccessWash Platform..."

echo "⏳ Waiting for database..."
while ! pg_isready -h $DB_HOST -p 5432 -U $DB_USER; do
    sleep 1
done
echo "✅ Database is ready!"

echo "🔄 Running migrations..."
python manage.py migrate --noinput

echo "👤 Setting up superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', '${ADMIN_EMAIL}', 'ChangeMe2024!')
    print('✅ Superuser created - Email: ${ADMIN_EMAIL}, Password: ChangeMe2024!')
else:
    print('✅ Superuser already exists')
"

echo "🌐 Starting Gunicorn server..."
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class gevent \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 30 \
    --keep-alive 2 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    accesswash_platform.wsgi:application
