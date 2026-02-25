release: python manage.py migrate
web: gunicorn bukudapur.wsgi:application --bind 0.0.0.0:$PORT