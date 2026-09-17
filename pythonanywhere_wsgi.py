# Copy this into the WSGI configuration file shown in PythonAnywhere's Web tab.
# Replace YOURUSERNAME and the project path with your actual values.

import os
import sys

path = "/home/YOURUSERNAME/kaldar"
if path not in sys.path:
    sys.path.insert(0, path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "expense_tracker.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
