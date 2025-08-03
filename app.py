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
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv
import logging
import time

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
# app.config['MAX_CONTENT_LENGTH'] = 100 * 1024  # 100KB limit for uploads to allow slight overhead
app.config['ADMIN_PASSWORD'] = os.getenv('ADMIN_PASSWORD')  
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 5,
    'max_overflow': 10,
    'pool_timeout': 30,
    'pool_pre_ping': True,
}

mail = Mail(app)
db.init_app(app)
mail.init_app(app)
migrate = Migrate(app, db) 

# Create database
with app.app_context():
    db.create_all()

def generate_access_code(length=5):
    """Generate a random 5-character alphanumeric access code."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form.get('admin_password')
        if password == app.config['ADMIN_PASSWORD']:
            session['admin_authenticated'] = True
            try:
                users = User.query.all()
                return render_template('admin.html', users=users)
            except OperationalError as e:
                logger.error(f"Database error in admin route: {str(e)}")
                flash('Database connection error. Please try again later.', 'error')
                return render_template('admin.html', users=None)
        else:
            flash('Incorrect admin password.', 'error')
            return render_template('admin.html', users=None)
    
    if not session.get('admin_authenticated'):
        return render_template('admin.html', users=None)
    
    try:
        users = User.query.all()
        return render_template('admin.html', users=users)
    except OperationalError as e:
        logger.error(f"Database error in admin route: {str(e)}")
        flash('Database connection error. Please try again later.', 'error')
        return render_template('admin.html', users=None)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        title = request.form['title']
        custom_title = request.form.get('custom_title', '')
        if title == 'Other(s)':
            if not custom_title:
                flash('Please provide a custom title for "Other(s)".', 'error')
                return render_template('register.html')
            if len(custom_title) > 10:
                flash('Custom title must not exceed 10 characters.', 'error')
                return render_template('register.html')
            title = custom_title
        first_name = request.form['first_name']
        family_name = request.form['family_name']
        company_organisation = request.form['company_organisation']
        country_of_origin = request.form['country_of_origin']
        telephone = request.form['telephone']
        email = request.form['email']
        confirm_email = request.form['confirm_email']
        age_group = request.form['age_group']
        highest_qualification = request.form['highest_qualification']
        registration_category = request.form['registration_category']
        hotel_lodging = request.form['hotel_lodging'] == 'Yes'
        travel_visa = request.form['travel_visa'] == 'Yes'
        further_info = request.form.get('further_info', '')
        picture_file = request.files.get('picture')

        if email != confirm_email:
            flash('Email and Confirm Email do not match.', 'error')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'error')
            return render_template('register.html')

        picture_data = None
        if picture_file:
            try:
                picture_data = base64.b64encode(picture_file.read()).decode('utf-8')
            except Exception as e:
                flash(f'Error processing image: {str(e)}', 'error')
                return render_template('register.html')

        token = generate_access_code()
        while User.query.filter_by(confirmation_token=token).first():
            token = generate_access_code()

        user = User(
            title=title,
            first_name=first_name,
            family_name=family_name,
            company_organisation=company_organisation,
            country_of_origin=country_of_origin,
            telephone=telephone,
            email=email,
            confirm_email=confirm_email,
            age_group=age_group,
            highest_qualification=highest_qualification,
            registration_category=registration_category,
            hotel_lodging=hotel_lodging,
            travel_visa=travel_visa,
            further_info=further_info,
            picture=picture_data,
            confirmation_token=token,
            is_approved=False,
            disapproval_reason=None
        )
        try:
            db.session.add(user)
            db.session.commit()
            send_user_receipt_email(email, first_name, family_name)
            send_admin_notification_email(email, token, title, first_name, family_name, company_organisation, country_of_origin, telephone, age_group, highest_qualification, registration_category, hotel_lodging, travel_visa, further_info, picture_data)
            
            flash('Your registration is received. A confirmation email will be sent to you shortly. Check your inbox, Spam or junk folders.', 'success')
            return redirect(url_for('index'))
        except OperationalError as e:
            logger.error(f"Database error in register route: {str(e)}")
            db.session.rollback()
            flash('Database connection error. Please try again later.', 'error')
            return render_template('register.html')

    return render_template('register.html')

@app.route('/approve/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    if not session.get('admin_authenticated'):
        flash('Please log in to the admin dashboard.', 'error')
        return redirect(url_for('admin'))

    user = User.query.get_or_404(user_id)
    if user.is_approved:
        flash(f'{user.first_name} {user.family_name} is already approved.', 'error')
        return redirect(url_for('admin'))

    user.is_approved = True
    user.disapproval_reason = None  # Clear any previous disapproval reason
    db.session.commit()

    send_user_confirmation_email(user.email, user.confirmation_token, user.first_name, user.family_name)
    flash(f'{user.first_name} {user.family_name} has been approved and confirmation email sent.', 'success')
    return redirect(url_for('admin'))

@app.route('/disapprove/<int:user_id>', methods=['POST'])
def disapprove_user(user_id):
    if not session.get('admin_authenticated'):
        flash('Please log in to the admin dashboard.', 'error')
        return redirect(url_for('admin'))

    user = User.query.get_or_404(user_id)
    disapproval_reason = request.form.get('disapproval_reason')
    
    if not disapproval_reason:
        flash('Please provide a reason for disapproval.', 'error')
        return redirect(url_for('admin'))

    user.is_approved = False
    user.disapproval_reason = disapproval_reason
    db.session.commit()

    send_user_disapproval_email(user.email, user.first_name, user.family_name, disapproval_reason)
    flash(f'{user.first_name} {user.family_name} has been disapproved.', 'success')
    return redirect(url_for('admin'))

@app.route('/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not session.get('admin_authenticated'):
        flash('Please log in to the admin dashboard.', 'error')
        return redirect(url_for('admin'))

    user = User.query.get_or_404(user_id)
    first_name = user.first_name
    family_name = user.family_name
    db.session.delete(user)
    db.session.commit()
    flash(f'{first_name} {family_name} has been deleted.', 'success')
    return redirect(url_for('admin'))

@app.route('/confirm/<token>')
def confirm_email(token):
    user = User.query.filter_by(confirmation_token=token).first()
    if user and user.is_approved:
        user.is_confirmed = True
        user.confirmation_token = ''
        db.session.commit()
        flash('Registration confirmed successfully!', 'success')
    else:
        flash('Invalid, unapproved, or expired confirmation link.', 'error')
    return redirect(url_for('index'))

def send_user_receipt_email(email, first_name, family_name):
    url = "https://api.brevo.com/v3/smtp/email"
    payload = json.dumps({
        "sender": {"name": "J.A.M Ltd", "email": app.config['EMAIL_FROM']},
        "to": [{"email": email, "name": f"{first_name} {family_name}"}],
        "subject": "Registration Received for Sustainable Energy Forum (SEF-2025)",
        "htmlContent": f"""
            <html>
            <head></head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <p>Dear {first_name} {family_name},</p>
                <p>Thank you for registering for the <strong>Sustainable Energy Forum (SEF-2025)</strong> in Abuja. Your registration has been received and is under review by our committee.</p>
                <p>You will receive a second email with your confirmation details and unique access code once your registration is approved.</p>
                <p><strong>For updates and to join the conversation, follow us:</strong></p>
                <ul>
                    <li>Via Instagram: <a href="https://www.instagram.com/jodor_a.m/">https://www.instagram.com/jodor_a.m/</a></li>
                    <li>Via LinkedIn: <a href="https://www.linkedin.com/jodor-a-m-ltd/">https://www.linkedin.com/jodor-a-m-ltd/</a></li>
                </ul>
                <p>We look forward to welcoming you!</p>
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
        print(f"Receipt email sent successfully: {response.json()}")
    else:
        print(f"Failed to send receipt email: {response.text}")

def send_user_confirmation_email(email, token, first_name, family_name):
    confirm_url = url_for('confirm_email', token=token, _external=True)
    url = "https://api.brevo.com/v3/smtp/email"
    payload = json.dumps({
        "sender": {"name": "J.A.M Ltd", "email": app.config['EMAIL_FROM']},
        "to": [{"email": email, "name": f"{first_name} {family_name}"}],
        "subject": "Your Registration for Sustainable Energy Forum (SEF-2025) is Approved",
        "htmlContent": f"""
            <html>
            <head></head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <p>Dear {first_name} {family_name},</p>
                <p>Congratulations! Thank you for registering to attend the <strong>Sustainable Energy Forum (SEF-2025)</strong> in Abuja – an exclusive gathering to showcase 
                Africas leading energy experts, Manufacturers, Energy traders, Product innovators for Oil & Gas, Renewables, Solar Systems & Hydro Power, 
                Geothermal & Biofuels, Control Technology & Telecommunications, Data Mining and Siesmic Mapping other energy sector leaders with sustainable solutions and breakthrough projects. 
            </p>
                <p><strong>Kindly find below your event details and unique access code for a smooth registration and check-in experience. Just come ready to be captivated.</strong></p>
                <ul>
                    <li><strong>Event Title:</strong> Sustainable Energy Forum (SEF-2025)</li>
                    <li><strong>Name:</strong> {first_name} {family_name}</li>
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
        print(f"Confirmation email sent successfully: {response.json()}")
    else:
        print(f"Failed to send confirmation email: {response.text}")

def send_user_disapproval_email(email, first_name, family_name, disapproval_reason):
    url = "https://api.brevo.com/v3/smtp/email"
    payload = json.dumps({
        "sender": {"name": "J.A.M Ltd", "email": app.config['EMAIL_FROM']},
        "to": [{"email": email, "name": f"{first_name} {family_name}"}],
        "subject": "Registration Status for Sustainable Energy Forum (SEF-2025)",
        "htmlContent": f"""
            <html>
            <head></head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <p>Dear {first_name} {family_name},</p>
                <p>Thank you for your interest in the <strong>Sustainable Energy Forum (SEF-2025)</strong> in Abuja.</p>
                <p>We regret to inform you that your registration has not been approved by our committee. The reason for this decision is: <strong>{disapproval_reason}</strong></p>
                <p><strong>For updates and to join the conversation, follow us:</strong></p>
                <ul>
                    <li>Via Instagram: <a href="https://www.instagram.com/jodor_a.m/">https://www.instagram.com/jodor_a.m/</a></li>
                    <li>Via LinkedIn: <a href="https://www.linkedin.com/jodor-a-m-ltd/">https://www.linkedin.com/jodor-a-m-ltd/</a></li>
                </ul>
                <p>We appreciate your understanding and hope to see you at future events.</p>
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
        print(f"Disapproval email sent successfully: {response.json()}")
    else:
        print(f"Failed to send disapproval email: {response.text}")

def send_admin_notification_email(email, token, title, first_name, family_name, company_organisation, country_of_origin, telephone, age_group, highest_qualification, registration_category, hotel_lodging, travel_visa, further_info, picture_data):
    url = "https://api.brevo.com/v3/smtp/email"
    payload = {
        "sender": {"name": "J.A.M Ltd", "email": app.config['EMAIL_FROM']},
        "to": [{"email": app.config['EMAIL_FROM'], "name": "J.A.M Ltd Admin"}],
        "subject": "New Registration for SEF-2025 (Pending Approval)",
        "htmlContent": f"""
            <html>
            <head></head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <p>Dear J.A.M Ltd Admin,</p>
                <p>A new user has registered for the Sustainable Energy Forum (SEF-2025) and is awaiting approval. Below are the details:</p>
                <ul>
                    <li><strong>Title:</strong> {title}</li>
                    <li><strong>First Name:</strong> {first_name}</li>
                    <li><strong>Family Name:</strong> {family_name}</li>
                    <li><strong>Company/Organisation/University:</strong> {company_organisation}</li>
                    <li><strong>Country of Origin:</strong> {country_of_origin}</li>
                    <li><strong>Email:</strong> {email}</li>
                    <li><strong>Telephone:</strong> {telephone}</li>
                    <li><strong>Age Group:</strong> {age_group}</li>
                    <li><strong>Highest Qualification:</strong> {highest_qualification}</li>
                    <li><strong>Registration Category:</strong> {registration_category}</li>
                    <li><strong>Hotel Lodging Required:</strong> {'Yes' if hotel_lodging else 'No'}</li>
                    <li><strong>Travel Visa Required:</strong> {'Yes' if travel_visa else 'No'}</li>
                    <li><strong>Further Info:</strong> {further_info or 'None'}</li>
                    <li><strong>Unique Access Code:</strong> {token}</li>
                </ul>
                <p>{'Profile picture is attached below.' if picture_data else 'No profile picture was uploaded.'}</p>
                <p>Please review and approve, disapprove, or delete this registration via the admin dashboard.</p>
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