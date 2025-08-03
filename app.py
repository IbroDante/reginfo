from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, render_template, session, get_flashed_messages, Response, make_response, send_file
from flask_sqlalchemy import SQLAlchemy
import requests
import json
import uuid
import os
from flask_mail import Mail, Message
from models import db, User
import base64
import json
import random
import string
import hmac
import hashlib
import socket
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import ssl
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, desc
import psycopg2, psycopg2cffi
from werkzeug.exceptions import RequestEntityTooLarge
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL") #render
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_SERVER'] = 'smtp-relay.brevo.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_DEFAULT_SENDER'] = ('PlugCap App', '929aca001@smtp-brevo.com')
app.config['BREVO_API_KEY'] = os.getenv('BREVO_API_KEY')
app.config['EMAIL_FROM'] = os.getenv('EMAIL_FROM')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024  # 100KB limit for uploads to allow slight overhead

mail = Mail(app)
db.init_app(app)
mail.init_app(app)
migrate = Migrate(app, db)  # Initialize Flask-Migrate

# Create database
with app.app_context():
    db.create_all()

# Custom handler for 413 Request Entity Too Large
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(error):
    flash('Profile picture must not exceed 50KB.', 'error')
    return redirect(url_for('register'))

def generate_access_code(length=5):
    """Generate a random 5-character alphanumeric access code."""
    characters = string.ascii_letters + string.digits  # a-z, A-Z, 0-9
    return ''.join(random.choice(characters) for _ in range(length))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        username = request.form['username']
        email = request.form['email']
        state = request.form['state']
        lga = request.form['lga']
        phone_number = request.form['phone_number']
        picture_file = request.files.get('picture')
        
        # Check if email or username already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'error')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Username already taken!', 'error')
            return redirect(url_for('register'))
        
        # Handle picture upload and enforce 50KB limit
        picture_data = None
        if picture_file:
            try:
                # Check file size
                picture_file.seek(0, os.SEEK_END)
                file_size = picture_file.tell()
                picture_file.seek(0)  # Reset file pointer
                if file_size > 50 * 1024:  # 50KB limit
                    flash('Profile picture must not exceed 50KB.', 'error')
                    return redirect(url_for('register'))
                picture_data = base64.b64encode(picture_file.read()).decode('utf-8')
            except Exception as e:
                flash(f'Error processing image: {str(e)}', 'error')
                return redirect(url_for('register'))
        
        # Generate 5-character access code
        token = generate_access_code()
        
        # Ensure the access code is unique
        while User.query.filter_by(confirmation_token=token).first():
            token = generate_access_code()
        
        # Create new user
        user = User(
            fullname=fullname,
            username=username,
            email=email,
            state=state,
            lga=lga,
            phone_number=phone_number,
            picture=picture_data,
            confirmation_token=token
        )
        db.session.add(user)
        db.session.commit()
        
        # Send confirmation emails to user and admin
        send_user_confirmation_email(email, token, fullname)
        send_admin_notification_email(email, token, fullname, picture_data)
        
        flash('Registration successful! Please check your email (Inbox, Spam or Junk) for confirmation. Thank you!', 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/confirm/<token>')
def confirm_email(token):
    user = User.query.filter_by(confirmation_token=token).first()
    
    if user:
        user.is_confirmed = True
        user.confirmation_token = ''
        db.session.commit()
        flash('Registration confirmed successfully!', 'success')
    else:
        flash('Invalid or expired confirmation link.', 'error')
    
    return redirect(url_for('index'))

def send_user_confirmation_email(email, token, fullname):
    confirm_url = url_for('confirm_email', token=token, _external=True)
    url = "https://api.brevo.com/v3/smtp/email"
    payload = json.dumps({
        "sender": {"name": "J.A.M Ltd", "email": app.config['EMAIL_FROM']},
        "to": [{"email": email, "name": fullname}],
        "subject": "Your Registration for Sustainable Energy Forum (SEF-2025)",
        "htmlContent": f"""
            <html>
            <head></head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <p>Dear {fullname},</p>
                <p>Thank you for registering to attend the <strong>Sustainable Energy Forum (SEF-2025)</strong> in Abuja – an exclusive gathering to showcase Africa's leading energy experts, manufacturers, energy traders, product innovators with solutions and breakthrough projects.</p>
                <p><strong>Kindly find below your event details and unique access code for a smooth registration and check-in experience. Just come ready to be captivated.</strong></p>
                <ul>
                    <li><strong>Event Title:</strong> Sustainable Energy Forum (SEF-2025)</li>
                    <li><strong>Name:</strong> {fullname}</li>
                    <li><strong>Date:</strong> September 29-30th, 2025</li>
                    <li><strong>Time:</strong> 10:00 AM (Daily)</li>
                    <li><strong>Venue:</strong> Central Business District, Abuja</li>
                    <li><strong>Unique Access Code:</strong> {token}</li>
                </ul>
                <p><strong>For updates and to join the conversation, follow us:</strong></p>
                <ul>
                    <li>Via Instagram: <a href="https://www.instagram.com/jodor_a.m/">https://www.instagram.com/jodor_a.m/</a></li>
                    <li>Via LinkedIn: <a href="https://www.linkedin.com/jodor-a-m-ltd/">https://www.linkedin.com/jodor-a-m-ltd/</a></li>
                </ul>
                <p>Our team @J.A.M Ltd and event partners is now looking forward to seeing you there!</p>
                <p>Best regards,</p>
                <p><strong>J.A.M Ltd</strong></p>
            </body>
            </html>
        """
    })
    headers = {
        "accept": "application/json",
        "api-key": app.config['BREVO_API_KEY'],
        "content-type": "application/json"
    }
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 201:
        print(f"User email sent successfully: {response.json()}")
    else:
        print(f"Failed to send user email: {response.text}")

def send_admin_notification_email(email, token, fullname, picture_data):
    url = "https://api.brevo.com/v3/smtp/email"
    payload = {
        "sender": {"name": "J.A.M Ltd", "email": app.config['EMAIL_FROM']},
        "to": [{"email": app.config['EMAIL_FROM'], "name": "J.A.M Ltd Admin"}],
        "subject": "New Registration for SEF-2025",
        "htmlContent": f"""
            <html>
            <head></head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <p>Dear J.A.M Ltd Admin,</p>
                <p>A new user has registered for the Sustainable Energy Forum (SEF-2025). Below are the details:</p>
                <ul>
                    <li><strong>Full Name:</strong> {fullname}</li>
                    <li><strong>Email:</strong> {email}</li>
                    <li><strong>Unique Access Code:</strong> {token}</li>
                </ul>
                <p>{'Profile picture is attached below.' if picture_data else 'No profile picture was uploaded.'}</p>
                <p>Best regards,</p>
                <p><strong>J.A.M Ltd Registration System</strong></p>
            </body>
            </html>
        """
    }
    if picture_data:
        payload["attachment"] = [{
            "content": picture_data,
            "name": "profile_picture.jpg"
        }]
    payload = json.dumps(payload)
    headers = {
        "accept": "application/json",
        "api-key": app.config['BREVO_API_KEY'],
        "content-type": "application/json"
    }
    response = requests.post(url, headers=headers, data=payload)
    if response.status_code == 201:
        print(f"Admin email sent successfully: {response.json()}")
    else:
        print(f"Failed to send admin email: {response.text}")

if __name__ == '__main__':
    app.run(debug=True)