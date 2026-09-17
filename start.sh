#!/bin/bash

set -e

echo "=== Starting Django deployment ==="

echo "Step 1: Running migrations..."
python manage.py migrate --settings=config.settings.prod

echo "Step 2: Creating superuser..."
python manage.py shell --settings=config.settings.prod -c "
import os
from django.contrib.auth.models import User
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f'Superuser {username} created')
else:
    print(f'Superuser {username} already exists')
"

echo "Step 3: Collecting static files..."
python manage.py collectstatic --noinput --settings=config.settings.prod

echo "Step 4: Starting server..."
gunicorn config.wsgi:application -c gunicorn.conf.py