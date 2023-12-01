# myapp/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import os
import logging
from logging.handlers import RotatingFileHandler

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure app
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI', 'sqlite:///tokens.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1 MB limit

# Initialize extensions
db = SQLAlchemy(app)
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

limiter.init_app(app)

# Logging configuration
logging.basicConfig(filename='app.log', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s: %(message)s')

# Import routes
from . import routes

# Other configurations and app-related code
# After defining your models and before starting the app
with app.app_context():
    db.create_all()
