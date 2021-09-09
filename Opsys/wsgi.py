"""
WSGI config for Opsys project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/howto/deployment/wsgi/
"""

import os
import sys
sys.stdout = sys.stderr
from os.path import abspath, dirname, join
from django.core.wsgi import get_wsgi_application
sys.path.append('/webapp/Opsys')
sys.path.append('/webapp/Opsys/Opsys')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Opsys.settings")
application = get_wsgi_application()
