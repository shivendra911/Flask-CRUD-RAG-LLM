# PythonAnywhere WSGI Configuration
# ──────────────────────────────────
# This file tells PythonAnywhere how to start your Flask app.
# On PythonAnywhere, go to:
#   Web tab → WSGI configuration file → replace contents with this.
#
# IMPORTANT: Update the paths below to match your PythonAnywhere username.

import sys
import os

# ── Set your PythonAnywhere username here ──────────────────────────────
USERNAME = "shivendra911"  # ← change if different

# Project path
project_home = f"/home/{USERNAME}/Flask-CRUD-RAG-LLM"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, ".env"))

# Import the Flask app
from run import app as application  # noqa
