import os
from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blood_donation_project.settings')

application = get_wsgi_application()