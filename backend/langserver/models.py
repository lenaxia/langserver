from datetime import datetime
import hashlib
from flask import current_app
from . import db

class APIToken(db.Model):
    id = db.Column(db.String(80), primary_key=True)
    token = db.Column(db.String(256), unique=True, nullable=False)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    rate_limit = db.Column(db.Integer, nullable=False, default='10')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Salt and hash the token
        admin_token = current_app.config.get('ADMIN_TOKEN', '')
        self.token = self.hash_token(self.token, admin_token)

    @staticmethod
    def hash_token(token, salt):
        return hashlib.sha256((token + salt).encode()).hexdigest()

    def __repr__(self):
        return f'<APIToken {self.id}>'
