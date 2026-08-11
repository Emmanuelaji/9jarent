release: python manage.py migrate --noinput
web: gunicorn nigerrents.wsgi:application --log-file -
