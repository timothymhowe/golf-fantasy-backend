import multiprocessing
import os
from dotenv import load_dotenv

# Load environment variables at config time
load_dotenv()

# Server socket
port = os.getenv("PORT", "8080")
bind = f"0.0.0.0:{port}"
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
timeout = 120

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Add some security headers
forwarded_allow_ips = '*'
secure_scheme_headers = {'X-Forwarded-Proto': 'https'}

# App loading
wsgi_app = "run:app"

# Development reload
reload = os.getenv("FLASK_ENV") == "development"

# Process naming
proc_name = "golf_pickem_api"

# Worker class
worker_class = "sync"

# SSL (uncomment for production with SSL)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"