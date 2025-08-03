from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json
import uuid
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(10), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    family_name = db.Column(db.String(100), nullable=False)
    company_organisation = db.Column(db.String(200), nullable=False)
    country_of_origin = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    confirm_email = db.Column(db.String(120), nullable=False)
    age_group = db.Column(db.String(10), nullable=False)
    highest_qualification = db.Column(db.String(50), nullable=False)
    registration_category = db.Column(db.String(50), nullable=False)
    hotel_lodging = db.Column(db.Boolean, nullable=False)
    travel_visa = db.Column(db.Boolean, nullable=False)
    further_info = db.Column(db.Text, nullable=True)
    picture = db.Column(db.Text, nullable=True)  # Base64 encoded image
    confirmation_token = db.Column(db.String(5), unique=True, nullable=True)
    is_confirmed = db.Column(db.Boolean, default=False)