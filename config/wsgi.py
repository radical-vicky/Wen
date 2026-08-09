"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

# Serverless hosts like Vercel don't give you a shell to run
# `manage.py migrate` after deploying, and tools like psycopg2 are often
# painful or impossible to install in restrictive local environments (e.g.
# Termux on Android) to run it from there either. So instead, we run
# migrations automatically once per cold start. This is safe to do
# repeatedly — Django's migrate command skips any migration that's already
# applied — and it's wrapped so a transient DB hiccup just means one
# request fails normally rather than crashing the whole app.
try:
    from django.core.management import call_command
    call_command('migrate', interactive=False, verbosity=0)
except Exception as _migrate_error:  # noqa: BLE001
    import logging
    logging.getLogger('django').warning('Auto-migrate on startup failed: %s', _migrate_error)
