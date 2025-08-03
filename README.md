# ExamApp - Local Server

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3.x-green.svg)

**ExamApp** is a Flask-based web application designed to manage and conduct exams on a local server. It supports user authentication, exam administration, question management, and response tracking with offline capabilities. The app integrates with a central server for question downloads and response uploads, and includes robust audit logging for security and tracking.

---

## Features

- **User Authentication**: Separate login for users and admins with CSRF protection.
- **Exam Management**: Admins can start/stop exams, download questions/users from a central server, and upload responses.
- **Exam Taking**: Users can take exams with a timer, navigate questions, and submit answers. Supports multiple categories.
- **Offline Support**: Answers are stored locally in `localStorage` when offline and synced when connectivity is restored. The timer pauses offline.
- **Audit Logging**: Every significant action (login, exam start/stop, answer save, etc.) is logged with details (user, IP, timestamp, etc.).
- **Performance Optimization**: Debounced AJAX calls for answer saving to reduce server load.
- **Security**: CSRF protection via Flask-WTF, secure session management with Flask-Login.
- **Real-Time Updates**: WebSocket support for exam state changes (e.g., start/stop notifications).
- **Caching**: Redis caching for frequently accessed data (e.g., questions, response counts).

---

## Prerequisites

- **Python**: 3.11 or higher
- **Redis**: For caching (optional but recommended)
- **PostgreSQL**: For the database (or adjust for SQLite)
- **Central Server**: A compatible central server for question/response syncing

---

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/ibrodante/examapp.git
cd examapp
```

### 2. Create a Virtual Environment
```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/examapp
CENTRAL_URL=http://central-server-url
CENTRAL_USERNAME=central-username
CENTRAL_PASSWORD=central-password
CACHE_REDIS_URL=redis://localhost:6379/0
```

- `SECRET_KEY`: A random string for session security.
- `DATABASE_URL`: Your database connection string.
- `CENTRAL_URL`, `CENTRAL_USERNAME`, `CENTRAL_PASSWORD`: For syncing with the central server.
- `CACHE_REDIS_URL`: Redis connection (optional).

### 5. Initialize the Database
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 6. Run Redis (Optional)
```bash
redis-server
```

### 7. Start the Application
```bash
python app.py
```
The app will run at `http://localhost:5000` by default.

---

## Usage

### Admin Features
1. **Login**: Go to `/admin/login`, enter admin credentials.
2. **Dashboard**: Access `/admin/dashboard` to:
   - Start/stop exams.
   - Download questions/users from the central server (`/download`).
   - Upload responses to the central server (`/upload`).
   - Register new users (`/register`).
   - View audit logs (`/admin/audit_logs`).
3. **Exam Control**: Use "Start Exam" or "Stop Exam" to manage the exam state.

### User Features
1. **Login**: Go to `/user/login`, enter your username.
2. **Home**: View exam status and response stats at `/`.
3. **Take Exam**: Go to `/play` to:
   - Answer questions with a 90-second timer per session.
   - Navigate between questions using buttons or keys (A-D for answers, N/P for next/prev).
   - Submit all answers or end the exam early.

### Offline Mode
- If offline, answers are saved in `localStorage` and the timer pauses.
- When back online, answers sync to the server automatically, and the timer resumes.

---

## Project Structure
```
examapp-local-server/
├── app.py              # Main application file
├── models.py           # Database models (User, Question, Response, etc.)
├── templates/          # HTML templates
│   ├── base.html
│   ├── user_login.html
│   ├── admin_login.html
│   ├── home.html
│   ├── play.html
│   ├── admin_dashboard.html
│   ├── register.html
│   ├── download.html
│   ├── upload.html
│   ├── audit_logs.html
│   └── done.html
├── logs/               # Log files (local.log)
├── migrations/         # Database migration files
├── .env                # Environment variables
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## Key Routes
- `/user/login`: User login page.
- `/admin/login`: Admin login page.
- `/`: Home page (requires login).
- `/play`: Exam-taking interface.
- `/admin/dashboard`: Admin dashboard.
- `/admin/audit_logs`: View audit logs.
- `/download`: Download questions/users from central server.
- `/upload`: Upload responses to central server.
- `/register`: Register new users (admin only).
- `/logout`: Log out.

---

## Development Notes

### Offline Behavior
- Answers are stored in `localStorage` when offline and synced when connectivity is restored.
- The timer stops offline and resumes online to ensure fairness.

### Performance
- AJAX calls for answer saving are debounced (2-second delay) to reduce server load.
- Redis caching is used for question lists and response counts.

### Security
- CSRF protection is enabled via Flask-WTF for all forms and AJAX requests.
- Audit logs track all actions for security and accountability.

### Known Limitations
- Requires a compatible central server for full functionality (not included).
- Offline answers persist in the browser until synced; closing the browser before syncing may lose data.
- Timer relies on client-side clock; server-side sync could enhance accuracy.

---

## Contributing
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.
