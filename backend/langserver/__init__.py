# langserver/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import os
import sys
import logging

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure app
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1 MB limit

# Set database URI
config_dir = "/config"
db_path = os.environ.get('DATABASE_URI', f'sqlite:///{config_dir}/tokens.db')
app.config['SQLALCHEMY_DATABASE_URI'] = db_path

# Check for ADMIN_TOKEN environment variable
admin_token = os.environ.get('ADMIN_TOKEN')
if not admin_token:
    logging.critical("ADMIN_TOKEN is not set. Terminating.")
    sys.exit("Fatal Error: ADMIN_TOKEN is not set.")
app.config['ADMIN_TOKEN'] = admin_token

# Environment variable for default rate limit
default_rate_limit_str = os.environ.get('DEFAULT_RATE_LIMIT', '10')
try:
    default_rate_limit = int(default_rate_limit_str)
    if default_rate_limit <= 0:
        raise ValueError
    app.config['DEFAULT_RATE_LIMIT'] = default_rate_limit
except ValueError:
    logging.error("Invalid DEFAULT_RATE_LIMIT value. Must be a positive integer. Falling back to default 10.")
    app.config['DEFAULT_RATE_LIMIT'] = 10

# Environment variable for log level
log_level = os.environ.get('LOGLEVEL', 'INFO').upper()

# Map string log level to logging level constants
log_level_dict = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# Validate log level and set default if invalid
if log_level not in log_level_dict:
    log_level = 'INFO'

# Set logging configuration
logging.basicConfig(
    level=log_level_dict[log_level],
    format='%(asctime)s %(levelname)s: %(message)s',
    stream=sys.stdout
)

# Initialize extensions
db = SQLAlchemy(app)
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
limiter.init_app(app)

# Import routes
from . import routes

# Other configurations and app-related code
# After defining your models and before starting the app
with app.app_context():
    db.create_all()
