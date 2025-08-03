JODOR Asset Management (J.A.M) Ltd Web Application
Overview
JODOR Asset Management (J.A.M) Ltd is a modern, forward-thinking asset management company focused on delivering exceptional investment solutions. This web application serves as the official platform for the Sustainable Energy Forum (SEF-2025) in Abuja, Nigeria, allowing users to register, receive a unique 5-character access code, and confirm their attendance via email. The application features a world-class, visually stunning landing page and a user-friendly registration form, both styled with Tailwind CSS, Poppins font, and enhanced with animations (AOS, Typed.js) and SweetAlert2 for flash messages.
Features

Landing Page (/):

Full-screen hero with animated gradient and typewriter effect for "JODOR Asset Management".
Sticky navigation with mobile hamburger menu.
About section with milestones and a gradient-overlay image.
Services section with animated cards and a testimonial carousel.
Call-to-action (CTA) with a 3D button for registration.
Social media links with animated icons (Instagram, LinkedIn).
Footer with newsletter signup (placeholder) and dynamic copyright year.


Registration Form (/register):

Collects user details: full name, username, email, state, LGA, phone number, and optional profile picture (≤50KB).
Displays validation errors and success messages via SweetAlert2 popups (success: green checkmark, error: yellow warning).
Modern design with Tailwind CSS, Poppins font, and Font Awesome icons.


Backend Functionality:

Generates a unique 5-character alphanumeric access code for each user.
Sends two emails via Brevo API:
User Email: SEF-2025 confirmation with event details and access code.
Admin Email: Notification to mololuwa.ibrahim@gmail.com with user details and optional picture attachment (profile_picture.jpg).


Validates profile picture size (≤50KB) with a custom 413 error handler for uploads exceeding 100KB.
Stores user data in a PostgreSQL or SQLite database using Flask-SQLAlchemy and Flask-Migrate.
Handles email confirmation via a unique token.


Technologies:

Backend: Flask, Flask-SQLAlchemy, Flask-Migrate, PostgreSQL/SQLite, Python.
Frontend: Tailwind CSS, Poppins font, Font Awesome, SweetAlert2, AOS, Typed.js.
APIs: Brevo for email delivery.
Environment: Managed via .env file with python-dotenv.



Prerequisites

Python 3.8+
PostgreSQL (optional, SQLite is fallback)
Brevo account with API key and verified sender email
Git for version control
Terminal or command-line interface

Setup Instructions

Clone the Repository:
git clone <repository-url>
cd jam-ltd-webapp


Install Dependencies:
pip install flask flask-sqlalchemy flask-migrate psycopg2-binary requests python-dotenv


Set Up Environment Variables:Create a .env file in the project root:
# .env
DATABASE_URL=postgresql://user:password@localhost:5432/your_database
SECRET_KEY=your-secret-key
BREVO_API_KEY=xkeysi
EMAIL_FROM=mololuwa.ibrahim@gmail.com


Replace DATABASE_URL with your PostgreSQL connection string or use sqlite:///users.db for SQLite.
Generate a secure SECRET_KEY.
Obtain BREVO_API_KEY from Brevo’s dashboard (API Keys section).
Ensure EMAIL_FROM is a verified sender in Brevo.


Set Up PostgreSQL (Optional):

Create a database:createdb your_database


Update DATABASE_URL in .env.


Initialize the Database:
export FLASK_APP=app.py
flask db init
flask db migrate -m "Initial migration"
flask db upgrade


Configure Brevo:

Log in to Brevo’s dashboard.
Verify the sender email (mololuwa.ibrahim@gmail.com) under Settings > Senders, Domains & Dedicated IPs.
Ensure the Brevo account is activated to send emails.


Run the Application:
python app.py


Access the app at http://localhost:5000.


Deployment (Optional):For deployment on Render:

Install gunicorn:pip install gunicorn


Set environment variables in Render’s dashboard.
Use the command:gunicorn --workers 3 app:app





File Structure
jam-ltd-webapp/
├── app.py                    # Flask application with routes, email logic, and error handling
├── models.py                 # SQLAlchemy User model for database
├── templates/
│   ├── index.html            # Landing page with hero, about, services, CTA, and social media
│   └── register.html         # Registration form with SweetAlert2 flash messages
├── .env                      # Environment variables (not tracked in git)
├── migrations/               # Flask-Migrate database migrations
└── README.md                 # This file

Usage

Landing Page:

Visit http://localhost:5000/ to view the J.A.M Ltd landing page.
Features a dynamic hero with a typewriter effect, animated services cards, testimonial carousel, and social media links.
Click "Register Now" to navigate to /register.


Registration:

At http://localhost:5000/register, fill in:
Full Name
Username
Email Address
State
LGA
Phone Number
Profile Picture (optional, ≤50KB)


Submit to register. SweetAlert2 popups display:
Success: "Registration successful! Please check your email for confirmation." (green checkmark).
Errors: e.g., "Profile picture must not exceed 50KB.", "Email already registered!" (yellow warning).




Emails:

User: Receives a confirmation email with SEF-2025 details (event title, date, venue, unique access code).
Admin: Receives a notification to mololuwa.ibrahim@gmail.com with user details and an optional picture attachment (profile_picture.jpg).


Confirmation:

Click the confirmation link in the user’s email to verify registration.
Redirects to / with a SweetAlert2 popup: "Registration confirmed successfully!".



Notes

Flash Messages: Both index.html and register.html use SweetAlert2 for consistent, modern popups (success: green checkmark, error: yellow warning, blue #3085d6 confirm button).
Design: The landing page features world-class aesthetics with animated gradients, AOS scroll effects, Typed.js typewriter, and a responsive mobile menu. The registration form uses Tailwind CSS for a sleek, professional look.
File Size Validation: Profile pictures are limited to 50KB, with a 100KB server limit (MAX_CONTENT_LENGTH). Exceeding either triggers a SweetAlert2 error popup.
Email Limits: Each registration sends two emails, counting toward Brevo’s 300 emails/day free plan limit.
Security:
The 50KB picture limit minimizes storage issues.
Add Flask-WTF for CSRF protection in production.
Verify EMAIL_FROM in Brevo.


Performance: Lazy-loaded images and minified CDNs (Tailwind, SweetAlert2, AOS, Typed.js) optimize load times.

Troubleshooting

Flash Messages: If SweetAlert2 popups fail, check the CDN (https://cdn.jsdelivr.net/npm/sweetalert2@11) and browser console.
Animations: Verify AOS (https://unpkg.com/aos@next) and Typed.js (https://cdnjs.cloudflare.com/ajax/libs/typed.js) CDNs. Ensure JavaScript is enabled.
File Size Errors: Test with files >50KB and >100KB to confirm SweetAlert2 error popups.
Email Issues: Check Brevo’s dashboard logs. Debug with print(response.text) in app.py.
Database: Verify DATABASE_URL or use SQLite. Rerun migrations if needed:flask db migrate -m "Update migration"
flask db upgrade



Future Enhancements

Implement a functional newsletter signup form in the footer using Brevo’s API.
Add client-side file size validation in register.html using JavaScript.
Develop a login system for the "Sign in" link in register.html.
Integrate additional animations or Lottie files for services icons.
Add a dashboard for admins to view registered users.

License
© 2025 JODOR Asset Management (J.A.M) Ltd. All rights reserved.

For support, contact: info@jamassetmgmt.com or +234 800 000 0000.