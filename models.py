from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json
import uuid
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

db = SQLAlchemy()

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    state = db.Column(db.String(80), nullable=False)
    lga = db.Column(db.String(80), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    picture = db.Column(db.Text, nullable=True)  # Store Base64 string
    is_confirmed = db.Column(db.Boolean, default=False)
    confirmation_token = db.Column(db.String(100), nullable=False)

# Create database
# with app.app_context():
#     db.create_all()