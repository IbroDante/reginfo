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
    title = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    family_name = db.Column(db.String(50), nullable=False)
    company_organisation = db.Column(db.String(100))
    country_of_origin = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    confirm_email = db.Column(db.String(120), nullable=False)
    age_group = db.Column(db.String(50), nullable=False)
    highest_qualification = db.Column(db.String(100), nullable=False)
    registration_category = db.Column(db.String(100), nullable=False)
    hotel_lodging = db.Column(db.Boolean, default=False)
    travel_visa = db.Column(db.Boolean, default=False)
    further_info = db.Column(db.Text)
    picture = db.Column(db.Text)
    confirmation_token = db.Column(db.String(5), unique=True)
    is_confirmed = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    disapproval_reason = db.Column(db.Text)  
    respond_contact = db.Column(db.Text)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    organisation = db.Column(db.String(100), nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    inquiry = db.Column(db.String(50), nullable=False)
    other_inquiry = db.Column(db.Text, nullable=True)
    message = db.Column(db.Text, nullable=True)
    respond_contact = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class BulkMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="Pending")
    progress = db.Column(db.Float, default=0.0)
    total_recipients = db.Column(db.Integer, default=0)
    sent_count = db.Column(db.Integer, default=0)
    attachment_name = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<BulkMessage {self.subject} ({self.status})>"
