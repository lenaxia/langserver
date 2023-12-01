from . import db


class APIToken(db.Model):
    id = db.Column(db.String(80), primary_key=True)
    token = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return '<APIToken %r>' % self.token
