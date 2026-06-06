# WSGI entry point — used by Gunicorn in production (teamboard.wsgi:application)
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teamboard.settings')
application = get_wsgi_application()
