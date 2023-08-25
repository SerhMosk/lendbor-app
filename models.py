from enum import Enum, auto
from datetime import datetime
from app import db


class TypeEnum(Enum):
    LEND = auto()
    BORROW = auto()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True)
    tg_id = db.Column(db.String(20))
    is_bot = db.Column(db.Boolean)
    language_code = db.Column(db.String(20))
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    password = db.Column(db.String)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=db.text('CURRENT_TIMESTAMP'))
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=db.text('CURRENT_TIMESTAMP'), onupdate=db.text('CURRENT_TIMESTAMP'))
    records = db.relationship('Record', backref='user', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)


class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    type = db.Column(db.Enum(TypeEnum), nullable=False)
    name = db.Column(db.String, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    remains = db.Column(db.Float, nullable=False)
    months = db.Column(db.Integer, nullable=False)
    payment_amount = db.Column(db.Float, nullable=False)
    payment_day = db.Column(db.Integer, nullable=False)
    last_date = db.Column(db.DateTime, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=db.text('CURRENT_TIMESTAMP'))
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=db.text('CURRENT_TIMESTAMP'), onupdate=db.text('CURRENT_TIMESTAMP'))
    payments = db.relationship('Payment', backref='record', lazy=True)


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    record_id = db.Column(db.Integer, db.ForeignKey('record.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    remains = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=db.text('CURRENT_TIMESTAMP'))
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=db.text('CURRENT_TIMESTAMP'), onupdate=db.text('CURRENT_TIMESTAMP'))
