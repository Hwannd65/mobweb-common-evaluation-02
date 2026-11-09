"""Prepare a new evaluation 02 environment; never changes the existing web app."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("hostname", help="PythonAnywhere hostname without https://")
args = parser.parse_args()
if "/" in args.hostname or not args.hostname.endswith(".pythonanywhere.com"):
    parser.error("Use the exact PythonAnywhere hostname, without a URL path")
root = Path(__file__).resolve().parents[1]
project = root / "PhotoBlogServer"
venv = Path.home() / ".virtualenvs" / "mobweb-02-venv"
config_path = Path.home() / ".config" / "mobweb-evaluation02.json"
config_path.parent.mkdir(parents=True, exist_ok=True)
if not config_path.exists():
    with open(config_path, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as file:
        json.dump({"hostname": args.hostname, "secret_key": secrets.token_urlsafe(64)}, file)
config = json.loads(config_path.read_text())
if config["hostname"] != args.hostname:
    raise SystemExit("Existing evaluation 02 config uses a different hostname; review it before continuing")
subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
python = str(venv / "bin" / "python")
subprocess.run([python, "-m", "pip", "install", "-r", str(project / "requirements.txt")], check=True)
env = {**os.environ, "DJANGO_SETTINGS_MODULE": "mysite.production_settings",
       "DJANGO_SECRET_KEY": config["secret_key"], "DJANGO_ALLOWED_HOSTS": config["hostname"]}
for command in [["check", "--deploy"], ["migrate", "--noinput"], ["collectstatic", "--noinput"]]:
    subprocess.run([python, "manage.py", *command], cwd=project, env=env, check=True)
print("Evaluation 02 prepared. Existing evaluation 01 files and live web configuration are unchanged.")
print("Next: create an evaluation 02 account, then review and switch the web app configuration.")
