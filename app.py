from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, render_template, session, get_flashed_messages, Response, make_response, send_file
from flask_sqlalchemy import SQLAlchemy
import requests
import json
import uuid
import os
from flask_mail import Mail, Message
from models import db, User, Contact
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
from sqlalchemy import or_, desc, func
import psycopg2, psycopg2cffi
from werkzeug.exceptions import RequestEntityTooLarge
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv
import logging
import time
import re
from datetime import datetime
import mimetypes
from celery import Celery

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

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

@app.route('/index2')
def index2():
    return render_template('index2.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form.get('admin_password')
        if password == app.config['ADMIN_PASSWORD']:
            session['admin_authenticated'] = True
            try:
                users = User.query.all()
                contacts = Contact.query.all()
                return render_template('admin.html', users=users, contacts=contacts)
            except OperationalError as e:
                logger.error(f"Database error in admin route: {str(e)}")
                flash('Database connection error. Please try again later.', 'error')
                return render_template('admin.html', users=None, contacts=None)
        else:
            flash('Incorrect admin password.', 'error')
            return render_template('admin.html', users=None, contacts=None)
    
    if not session.get('admin_authenticated'):
        return render_template('admin.html', users=None, contacts=None)
    
    try:
        users = User.query.all()
        contacts = Contact.query.all()
        return render_template('admin.html', users=users, contacts=contacts)
    except OperationalError as e:
        logger.error(f"Database error in admin route: {str(e)}")
        flash('Database connection error. Please try again later.', 'error')
        return render_template('admin.html', users=None, contacts=None)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form_data = {}
    if request.method == 'POST':
        form_data = request.form.to_dict()
        title = form_data.get('title')
        custom_title = form_data.get('custom_title', '')
        if title == 'Other(s)':
            if not custom_title:
                return jsonify({'status': 'error', 'message': 'Please provide a custom title for "Other(s)".'}), 400
            if len(custom_title) > 10:
                return jsonify({'status': 'error', 'message': 'Custom title must not exceed 10 characters.'}), 400
            form_data['title'] = custom_title
            title = custom_title
        first_name = form_data.get('first_name')
        family_name = form_data.get('family_name')
        company_organisation = form_data.get('company_organisation')
        country_of_origin = form_data.get('country_of_origin')
        telephone = form_data.get('telephone')
        email = form_data.get('email').lower()  # Normalize email to lowercase
        confirm_email = form_data.get('confirm_email').lower()
        age_group = form_data.get('age_group')
        highest_qualification = form_data.get('highest_qualification')
        registration_category = form_data.get('registration_category')
        hotel_lodging = form_data.get('hotel_lodging') == 'Yes'
        travel_visa = form_data.get('travel_visa') == 'Yes'
        certificate_required = form_data.get('certificate_required') == 'Yes'
        further_info = form_data.get('further_info', '')
        picture_file = request.files.get('picture')

        if email != confirm_email:
            return jsonify({'status': 'error', 'message': 'Email and Confirm Email do not match.'}), 400

        # Case-insensitive email check
        existing_user = User.query.filter(func.lower(User.email) == email).first()
        if existing_user:
            logger.info(f"Email check: Found existing email {email} in database")
            return jsonify({'status': 'error', 'message': 'Email already registered! Please use a different email.'}), 400
        else:
            logger.info(f"Email check: No existing email found for {email}")

        picture_data = None
        if picture_file:
            try:
                picture_data = base64.b64encode(picture_file.read()).decode('utf-8')
            except Exception as e:
                logger.error(f"Error processing image for {email}: {str(e)}")
                return jsonify({'status': 'error', 'message': f'Error processing image: {str(e)}'}), 400

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
            certificate_required=certificate_required,
            further_info=further_info,
            picture=picture_data,
            confirmation_token=token,
            is_approved=False,
            disapproval_reason=None
        )
        try:
            db.session.add(user)
            db.session.commit()
            logger.info(f"User registered successfully: {email}")
            send_user_receipt_email(email, first_name, family_name)
            send_admin_notification_email(email, token, title, first_name, family_name, company_organisation, country_of_origin, telephone, age_group, highest_qualification, registration_category, hotel_lodging, travel_visa, certificate_required, further_info, picture_data)
            return jsonify({
                'status': 'success',
                'message': 'Your registration is received. A confirmation email will be sent to you shortly. Check your inbox, Spam or junk folders.'
            }), 200
        except OperationalError as e:
            logger.error(f"Database error in register route for {email}: {str(e)}")
            db.session.rollback()
            return jsonify({'status': 'error', 'message': 'Database connection error. Please try again later.'}), 500

    return render_template('register.html', form_data=form_data)

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
    user.disapproval_reason = None
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

# Delete Contact Route
@app.route('/delete_contact/<int:contact_id>', methods=['POST'])
def delete_contact(contact_id):
    if not session.get('admin_authenticated'):
        flash('Please log in to the admin dashboard.', 'error')
        return redirect(url_for('admin'))

    contact = Contact.query.get_or_404(contact_id)
    name = contact.name
    try:
        db.session.delete(contact)
        db.session.commit()
        flash(f'Contact inquiry from {name} has been deleted.', 'success')
        logger.info(f"Deleted contact ID {contact_id} for {name}")
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete contact: {str(e)}', 'error')
        logger.error(f"Failed to delete contact ID {contact_id}: {str(e)}")
    return redirect(url_for('admin'))
    
@app.route('/third_mail/<int:user_id>', methods=['POST'])
def third_mail(user_id):
    if not session.get('admin_authenticated'):
        flash('Please log in to the admin dashboard.', 'error')
        return redirect(url_for('admin'))

    user = User.query.get_or_404(user_id)
    response_message = request.form.get('response_message')  # Matches frontend

    if not response_message:
        flash('Please provide a response message.', 'error')
        logger.warning(f"Response message missing for contact ID {user_id}")
        return redirect(url_for('admin'))

    try:
        user.respond_contact = response_message
        db.session.commit()
        logger.info(f"Stored response for contact ID {user_id}: {response_message}")

        # Send response email
        if send_user_respond_email(
            user.title,
            user.first_name,
            user.family_name,
            user.company_organisation,
            user.country_of_origin,
            user.telephone,
            user.email,
            user.confirm_email,
            user.age_group,
            user.highest_qualification,
            user.registration_category,
            user.hotel_lodging,
            user.travel_visa,
            user.further_info,
            user.picture,
            user.confirmation_token,
            user.is_confirmed,
            user.is_approved,
            user.disapproval_reason,
            user.respond_contact,
            response_message
        ):
            flash(f'Response sent to {user.first_name} {user.family_name} successfully.', 'success')
        else:
            flash(f'Response saved for {user.first_name} {user.family_name}, but failed to send email.', 'error')
            logger.error(f"Failed to send response email for contact ID {user_id}")
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to process response: {str(e)}', 'error')
        logger.error(f"Database error for contact ID {user_id}: {str(e)}")
    return redirect(url_for('admin'))

# Respond Contact Route
@app.route('/respond_contact/<int:contact_id>', methods=['POST'])
def respond_contact(contact_id):
    if not session.get('admin_authenticated'):
        flash('Please log in to the admin dashboard.', 'error')
        return redirect(url_for('admin'))

    contact = Contact.query.get_or_404(contact_id)
    response_message = request.form.get('response_message')  # Matches frontend

    if not response_message:
        flash('Please provide a response message.', 'error')
        logger.warning(f"Response message missing for contact ID {contact_id}")
        return redirect(url_for('admin'))

    try:
        contact.respond_contact = response_message
        db.session.commit()
        logger.info(f"Stored response for contact ID {contact_id}: {response_message}")

        # Send response email
        if send_contact_respond_email(
            contact.name,
            contact.organisation,
            contact.telephone,
            contact.email,
            contact.inquiry,
            contact.other_inquiry,
            contact.message,
            response_message
        ):
            flash(f'Response sent to {contact.name} successfully.', 'success')
        else:
            flash(f'Response saved for {contact.name}, but failed to send email.', 'error')
            logger.error(f"Failed to send response email for contact ID {contact_id}")
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to process response: {str(e)}', 'error')
        logger.error(f"Database error for contact ID {contact_id}: {str(e)}")
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

def send_user_respond_email(title, first_name, family_name, company_organisation, country_of_origin, telephone, email, confirm_email, age_group, highest_qualification, registration_category, hotel_lodging, travel_visa, further_info, picture, confirmation_token, is_confirmed, is_approved, disapproval_reason, respond_contact, response_message):
    url = "https://api.brevo.com/v3/smtp/email"
    payload = {
        "sender": {"name": "J.A.M Ltd", "email": app.config['EMAIL_FROM']},
        "to": [{"email": email, "name": f"{first_name} {family_name}"}],
        "subject": "Venue Confirmation for Sustainable Energy Forum (SEF-2025)",
        "htmlContent": f"""
            <html>
            <head></head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <p>Dear {first_name} {family_name},</p>
                <p>Thank you for your registration regarding the <strong>Sustainable Energy Forum (SEF-2025)</strong> in Abuja. heres the venue:</p>
                <p><strong>Venue:</strong> {response_message}</p>
                <p><strong>Kindly find below your event details and unique access code for a smooth registration and check-in experience. Just come ready to be captivated.</strong></p>
                <ul>
                    <li><strong>Event Title:</strong> Sustainable Energy Forum (SEF-2025)</li>
                    <li><strong>Name:</strong> {first_name} {family_name}</li>
                    <li><strong>Date:</strong> September 29-30th, 2025</li>
                    <li><strong>Time:</strong> 10:00 AM (Daily)</li>
                    <li><strong>Venue:</strong> Central Business District, Abuja</li>
                    <li><strong>Unique Access Code:</strong> {confirmation_token}</li>

                </ul>
                <p><strong>For updates and to join the conversation, follow us:</strong></p>
                <ul>
                    <li>Via Instagram: <a href="https://www.instagram.com/jodor_a.m/">https://www.instagram.com/jodor_a.m/</a></li>
                    <li>Via LinkedIn: <a href="https://www.linkedin.com/jodor-a-m-ltd/">https://www.linkedin.com/jodor-a-m-ltd/</a></li>
                </ul>
                <p>We appreciate your interest and look forward to assisting you further.</p>
                <p>Best regards,</p>
                <p><strong>J.A.M Ltd Team</strong></p>
            </body>
            </html>
        """
    }
    headers = {
        "accept": "application/json",
        "api-key": app.config['BREVO_API_KEY'],
        "content-type": "application/json"
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)  # Add timeout
        if response.status_code == 201:
            logger.info(f"user third responce email sent successfully to {email}: {response.json()}")
            return True
        else:
            logger.error(f"Failed to send third response email to {email}: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Exception while sending third response email to {email}: {str(e)}")
        return False

def send_contact_respond_email(name, organisation, telephone, email, inquiry, other_inquiry, message, response_message):
    url = "https://api.brevo.com/v3/smtp/email"
    payload = {
        "sender": {"name": "J.A.M Ltd", "email": app.config['EMAIL_FROM']},
        "to": [{"email": email, "name": name}],
        "subject": "Response to Your Inquiry for Sustainable Energy Forum (SEF-2025)",
        "htmlContent": f"""
            <html>
            <head></head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <p>Dear {name},</p>
                <p>Thank you for your inquiry regarding the <strong>Sustainable Energy Forum (SEF-2025)</strong> in Abuja. We have reviewed your submission, and our response is below:</p>
                <p><strong>Our Response:</strong> {response_message}</p>
                <p><strong>Your Inquiry Details:</strong></p>
                <ul>
                    <li><strong>Name:</strong> {name}</li>
                    <li><strong>Organisation:</strong> {organisation}</li>
                    <li><strong>Telephone:</strong> {telephone}</li>
                    <li><strong>Email:</strong> {email}</li>
                    <li><strong>Inquiry Type:</strong> {inquiry}</li>
                    <li><strong>Other Inquiry Details:</strong> {other_inquiry or 'None'}</li>
                    <li><strong>Message:</strong> {message or 'None'}</li>
                </ul>
                <p><strong>For updates and to join the conversation, follow us:</strong></p>
                <ul>
                    <li>Via Instagram: <a href="https://www.instagram.com/jodor_a.m/">https://www.instagram.com/jodor_a.m/</a></li>
                    <li>Via LinkedIn: <a href="https://www.linkedin.com/jodor-a-m-ltd/">https://www.linkedin.com/jodor-a-m-ltd/</a></li>
                </ul>
                <p>We appreciate your interest and look forward to assisting you further.</p>
                <p>Best regards,</p>
                <p><strong>J.A.M Ltd Team</strong></p>
            </body>
            </html>
        """
    }
    headers = {
        "accept": "application/json",
        "api-key": app.config['BREVO_API_KEY'],
        "content-type": "application/json"
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)  # Add timeout
        if response.status_code == 201:
            logger.info(f"Contact response email sent successfully to {email}: {response.json()}")
            return True
        else:
            logger.error(f"Failed to send contact response email to {email}: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Exception while sending contact response email to {email}: {str(e)}")
        return False

def send_admin_notification_email(email, token, title, first_name, family_name, company_organisation, country_of_origin, telephone, age_group, highest_qualification, registration_category, hotel_lodging, travel_visa, certificate_required, further_info, picture_data):
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
                    <li><strong>Certificate Required:</strong> {'Yes' if certificate_required else 'No'}</li>

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

# Email sending function for contact inquiries
def send_contact_notification_email(name, organisation, telephone, email, inquiry, other_inquiry, message, timestamp):
    url = "https://api.brevo.com/v3/smtp/email"
    payload = {
        "sender": {"name": "J.A.M Ltd", "email": app.config['EMAIL_FROM']},
        "to": [{"email": app.config['EMAIL_FROM'], "name": "J.A.M Ltd Admin"}],
        "subject": "New Contact Inquiry from J.A.M Ltd Website",
        "htmlContent": f"""
            <html>
            <head></head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <p>Dear J.A.M Ltd Admin,</p>
                <p>A new contact inquiry has been submitted via the website. Below are the details:</p>
                <ul>
                    <li><strong>Name:</strong> {name}</li>
                    <li><strong>Organisation:</strong> {organisation}</li>
                    <li><strong>Telephone:</strong> {telephone}</li>
                    <li><strong>Email:</strong> {email}</li>
                    <li><strong>Nature of Inquiry:</strong> {inquiry}</li>
                    <li><strong>Other Inquiry Details:</strong> {other_inquiry or 'None'}</li>
                    <li><strong>Message:</strong> {message or 'None'}</li>
                    <li><strong>Timestamp:</strong> {timestamp}</li>
                </ul>
                <p>Please review and respond to this inquiry as needed.</p>
                <p>Best regards,</p>
                <p><strong>J.A.M Ltd Contact System</strong></p>
            </body>
            </html>
        """
    }
    payload = json.dumps(payload)
    headers = {
        "accept": "application/json",
        "api-key": app.config['BREVO_API_KEY'],
        "content-type": "application/json"
    }
    try:
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 201:
            logger.info(f"Contact email sent successfully to {app.config['EMAIL_FROM']}: {response.json()}")
            return True
        else:
            logger.error(f"Failed to send contact email: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Exception while sending contact email: {str(e)}")
        return False

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        organisation = request.form['organisation']
        telephone = request.form['telephone']
        email = request.form['email']
        inquiry = request.form['inquiry']
        other_inquiry = request.form.get('other_inquiry', '')
        message = request.form.get('message', '')

        # Validate email format
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            flash('Invalid email address.', 'warning')
            logger.error(f"Invalid email format: {email}")
            return render_template('index.html')

        # Validate other_inquiry if inquiry is "Other Inquiry"
        if inquiry == 'Other Inquiry' and not other_inquiry.strip():
            flash('Please provide details for Other Inquiry.', 'warning')
            logger.error("Other Inquiry selected but no details provided")
            return render_template('index.html')

        # Store contact inquiry
        contact_entry = Contact(
            name=name,
            organisation=organisation,
            telephone=telephone,
            email=email,
            inquiry=inquiry,
            other_inquiry=other_inquiry if other_inquiry.strip() else None,
            message=message if message.strip() else None

        )
        try:
            db.session.add(contact_entry)
            db.session.commit()
            logger.info(f"Contact inquiry stored: {name}, {email}, {inquiry}")
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to store inquiry: {str(e)}', 'warning')
            logger.error(f"Database error: {str(e)}")
            return render_template('index.html')

        # Send email to admin
        if send_contact_notification_email(
            name=name,
            organisation=organisation,
            telephone=telephone,
            email=email,
            inquiry=inquiry,
            other_inquiry=other_inquiry,
            message=message,
            timestamp=contact_entry.timestamp
        ):
            flash('Your inquiry has been submitted successfully. We will contact you soon.', 'success')
        else:
            flash('Inquiry saved, but failed to send email to admin. Please try again later.', 'warning')
            logger.error("Contact email sending failed, but inquiry was saved")

        return render_template('index.html')
    return render_template('index.html')

@app.route('/send_bulk_email', methods=['POST'])
def send_bulk_email():
    if not session.get('admin_authenticated'):
        flash('Please log in to the admin dashboard.', 'error')
        return redirect(url_for('admin'))

    subject = request.form.get('subject')
    message_body = request.form.get('message')
    file = request.files.get('attachment')

    users = User.query.all()
    if not users:
        flash("No users found to send email.", "warning")
        return redirect(url_for('admin'))

    recipients = [{"email": u.email, "name": f"{u.first_name} {u.family_name}"} for u in users if u.email]

    payload = {
        "sender": {"name": "J.A.M Ltd", "email": app.config['EMAIL_FROM']},
        "to": recipients,
        "subject": subject,
        "htmlContent": f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f9f9f9; padding: 20px;">
                <div style="max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
                    <h2 style="color: #1e40af; text-align: center; margin-bottom: 20px;">📢 Official Announcement from J.A.M Ltd</h2>
                    <hr>
                    <p><strong>Event:</strong> Sustainable Energy Forum (SEF-2025)<br>
                    <strong>Date:</strong> September 29-30th, 2025<br>
                    <strong>Venue:</strong> Central Business District, Abuja</p>
                    <strong>Message :</strong> {message_body}</p>

                    <p style="font-size: 12px; color: #777;">Stay connected: 
                        <a href="https://www.instagram.com/jodor_a.m/">Instagram</a> | 
                        <a href="https://www.linkedin.com/jodor-a-m-ltd/">LinkedIn</a>
                    </p>
                </div>
            </body>
            </html>
        """
    }

    # If admin uploaded a file, attach it
    if file and file.filename:
        try:
            file_data = base64.b64encode(file.read()).decode('utf-8')
            mime_type, _ = mimetypes.guess_type(file.filename)
            payload["attachment"] = [{
                "content": file_data,
                "name": file.filename,
                "type": mime_type or "application/octet-stream"
            }]
        except Exception as e:
            logger.error(f"Attachment processing failed: {e}")
            flash("Error processing attachment. Email sent without it.", "warning")

    headers = {
        "accept": "application/json",
        "api-key": app.config['BREVO_API_KEY'],
        "content-type": "application/json"
    }

    try:
        response = requests.post("https://api.brevo.com/v3/smtp/email", headers=headers, data=json.dumps(payload), timeout=15)
        if response.status_code == 201:
            flash("Bulk email sent successfully!", "success")
        else:
            logger.error(f"Bulk email failed: {response.text}")
            flash("Failed to send bulk email. Check logs.", "error")
    except Exception as e:
        logger.error(f"Bulk email exception: {str(e)}")
        flash("An error occurred while sending emails.", "error")

    return redirect(url_for('admin'))

# def make_celery(app):
#     celery = Celery(
#         app.import_name,
#         broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
#         backend=os.getenv("REDIS_URL", "redis://localhost:6379/0")
#     )
#     celery.conf.update(app.config)
#     TaskBase = celery.Task

#     class ContextTask(TaskBase):
#         def __call__(self, *args, **kwargs):
#             with app.app_context():
#                 return TaskBase.__call__(self, *args, **kwargs)

#     celery.Task = ContextTask
#     return celery

# celery = make_celery(app)

# @celery.task(bind=True, max_retries=5)
# def send_bulk_email_task(self, subject, message_body, recipients, attachment=None, batch_size=50):
#     """
#     Background task to send bulk emails via Brevo API in batches.
#     Retries failed batches automatically with exponential backoff.
#     """
#     url = "https://api.brevo.com/v3/smtp/email"
#     headers = {
#         "accept": "application/json",
#         "api-key": app.config['BREVO_API_KEY'],
#         "content-type": "application/json"
#     }

#     total = len(recipients)
#     sent = 0

#     for i in range(0, total, batch_size):
#         batch = recipients[i:i+batch_size]

#         payload = {
#             "sender": {"name": "J.A.M Ltd", "email": app.config['EMAIL_FROM']},
#             "to": batch,
#             "subject": subject,
#             "htmlContent": f"""
#                 <html>
#                 <body>
#                     <h2>Announcement from J.A.M Ltd</h2>
#                     <p>{message_body}</p>
#                     <hr>
#                     <p><strong>Event:</strong> Sustainable Energy Forum (SEF-2025)<br>
#                        <strong>Date:</strong> Sept 29–30, 2025<br>
#                        <strong>Venue:</strong> Abuja</p>
#                 </body>
#                 </html>
#             """
#         }

#         if attachment:
#             payload["attachment"] = [attachment]

#         try:
#             response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)

#             if response.status_code != 201:
#                 # Retry with exponential backoff (2^retries seconds)
#                 raise Exception(f"Brevo responded {response.status_code}: {response.text}")

#         except Exception as e:
#             countdown = 2 ** self.request.retries  # exponential backoff
#             app.logger.warning(f"Batch {i//batch_size+1} failed, retrying in {countdown}s... Error: {e}")
#             raise self.retry(exc=e, countdown=countdown)

#         # Update progress after each successful batch
#         sent += len(batch)
#         self.update_state(state="PROGRESS", meta={"current": sent, "total": total})

#     return {"current": total, "total": total, "status": "All batches sent"}

# @app.route('/bulk_status/<task_id>')
# def bulk_status(task_id):
#     task = send_bulk_email_task.AsyncResult(task_id)
#     if task.state == "PENDING":
#         response = {"state": task.state, "progress": 0}
#     elif task.state != "FAILURE":
#         response = {
#             "state": task.state,
#             "progress": (task.info.get("current", 0) / task.info.get("total", 1)) * 100,
#             "current": task.info.get("current", 0),
#             "total": task.info.get("total", 1),
#         }
#     else:
#         response = {"state": "FAILURE", "error": str(task.info)}

#     return jsonify(response)

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
