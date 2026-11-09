"""PythonAnywhere WSGI entry point for evaluation 02, independent of evaluation 01."""
import json
import os
import sys
from pathlib import Path

home = Path.home()
project = home / "common-evaluation-02" / "PhotoBlogServer"
config = json.loads((home / ".config" / "mobweb-evaluation02.json").read_text())
sys.path.insert(0, str(project))
os.environ["DJANGO_SETTINGS_MODULE"] = "mysite.production_settings"
os.environ["DJANGO_SECRET_KEY"] = config["secret_key"]
os.environ["DJANGO_ALLOWED_HOSTS"] = config["hostname"]

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
