<p align="center">
  <img src="static/clg_logo_nobg.png" alt="Plan-Bendora Logo" width="120" />
</p>

<h1 align="center">Plan-Bendora 🎓</h1>

<p align="center">
  <strong>Automate. Allocate. Achieve.</strong><br/>
  A robust, secure, and modern web application built with <b>Flask</b> for automating the course allocation process for university students.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white" alt="SQLAlchemy" />
  <img src="https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge" alt="MIT License" />
</p>

<p align="center">
  <a href="#-key-features">Features</a> •
  <a href="#%EF%B8%8F-tech-stack">Tech Stack</a> •
  <a href="#%EF%B8%8F-installation--setup">Installation</a> •
  <a href="#-environment-variables">Configuration</a> •
  <a href="#-api-routes-overview">API Routes</a> •
  <a href="#-troubleshooting">Troubleshooting</a>
</p>

---

## ✨ Overview

The system ensures **fairness and efficiency** by using a **First-Come-First-Serve (FCFS)** based matching algorithm, prioritizing students based on their submission timestamp. It provides a complete end-to-end workflow — from student registration with **email OTP verification**, to preference submission, automated allocation, and downloadable reports.

---

## 🚀 Key Features

### 🛡️ For Administrators

| Feature                    | Description                                                                                                                 |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **One-Click Allocation**   | Execute the FCFS-based allocation algorithm with a single click. Students are prioritized strictly by submission timestamp. |
| **Course Management**      | Add, edit, and delete courses with real-time capacity tracking and optional faculty assignment.                             |
| **Student Management**     | Bulk upload students via **Excel/CSV**, manually edit or delete student profiles, and view detailed student records.        |
| **Allocation Time Window** | Set a configurable start and end time for when students can submit preferences.                                             |
| **Re-submission Toggle**   | Enable or disable the ability for students to change their course preferences.                                              |
| **Notice Board**           | Publish notices (info, deadline, maintenance) that appear on student dashboards.                                            |
| **Analytics Dashboard**    | Visualize course demand vs. capacity, allocation success/satisfaction rates, and faculty load distribution.                 |
| **Export Reports**         | Download comprehensive **Excel** (`.xlsx`) and professional **PDF** reports of allocation results.                          |
| **Per-Course Export**      | Export a detailed Excel sheet for any individual course showing all its allocated students.                                 |
| **System Reset**           | Clear all students, courses, and generated reports to prepare for a new allocation cycle.                                   |

### 🎓 For Students

| Feature                    | Description                                                                                         |
| -------------------------- | --------------------------------------------------------------------------------------------------- |
| **Secure Registration**    | Self-registration with **email OTP verification** (powered by [Brevo API](https://www.brevo.com/)). |
| **Flexible Login**         | Log in using either Student ID or registered email address.                                         |
| **Preference Submission**  | Rank up to **8 course preferences** via an intuitive, interactive selection interface.              |
| **Smart Recommendations**  | Get course suggestions based on seat availability to help guide choices.                            |
| **Personalized Dashboard** | View allocation status, assigned course, profile details, and admin notices.                        |
| **Mobile Responsive**      | Fully optimized Glassmorphism UI for phones, tablets, and desktops.                                 |

### 🔒 Security

- **Password Hashing** — Werkzeug's `generate_password_hash` / `check_password_hash`
- **CSRF Protection** — Flask-WTF CSRFProtect on all forms
- **Rate Limiting** — Flask-Limiter (500/day, 50/hour global; 5/hour for OTP)
- **Role-Based Access Control** — Strict admin/student route separation
- **Input Validation** — Server-side regex validation for UserID (12-digit), email, mobile (10-digit), name, etc.
- **Privilege Escalation Prevention** — Role field is never accepted from form input

---

## 🛠️ Tech Stack

| Layer              | Technology                                                             |
| ------------------ | ---------------------------------------------------------------------- |
| **Backend**        | Python 3.10+, Flask 3.1, SQLAlchemy 2.0 (ORM)                          |
| **Database**       | SQLite (default, zero-config) / PostgreSQL (production via `psycopg2`) |
| **Frontend**       | HTML5, CSS3 (Custom Glassmorphism Design), Vanilla JavaScript          |
| **Authentication** | Flask-Login, Werkzeug Security, OTP via Brevo Transactional Email API  |
| **Reporting**      | ReportLab (PDF generation), Pandas + OpenPyXL (Excel generation)       |
| **Security**       | Flask-WTF (CSRF), Flask-Limiter (Rate Limiting)                        |
| **Dev Tools**      | LiveReload (auto browser refresh), python-dotenv (.env loading)        |
| **Production**     | Gunicorn WSGI server                                                   |

---

## ⚙️ Installation & Setup

### Prerequisites

- Python **3.10** or higher
- `pip` package manager
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/Shubham00043/Plan-Bendora.git
cd Plan-Bendora
```

### 2. Create a Virtual Environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example `.env` file and customize it:

```bash
cp .env.example .env
```

Then edit `.env` with your values (see [Environment Variables](#-environment-variables) below).

### 5. Initialize the Database

```bash
flask init-db
```

> **Output:** `Admin user created with username 'admin'` → `Database initialized successfully.`

### 6. Run the Application

**Development (with live reload):**

```bash
python app.py
```

**Production (with Gunicorn):**

```bash
gunicorn app:app --bind 0.0.0.0:5000
```

Visit **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser. 🚀

---

## 🔐 Environment Variables

Create a `.env` file in the project root (see `.env.example`):

| Variable         | Required      | Default        | Description                                                       |
| ---------------- | ------------- | -------------- | ----------------------------------------------------------------- |
| `SECRET_KEY`     | ✅ Yes (prod) | Auto-generated | Flask secret key for session security                             |
| `FLASK_DEBUG`    | No            | `0`            | Set to `1` for development mode                                   |
| `DATABASE_URL`   | ✅ Yes        | —              | Database connection string (e.g. `sqlite:///smart_allocation.db`) |
| `ADMIN_PASSWORD` | No            | `admin123`     | Initial admin account password                                    |
| `BREVO_API_KEY`  | No            | —              | Brevo API key for OTP email delivery                              |
| `MAIL_USERNAME`  | No            | —              | Sender email address for OTP emails                               |

> ⚠️ **Important:** Change `SECRET_KEY` and `ADMIN_PASSWORD` before deploying to production!

---

## 🔑 Default Credentials

### Admin Account

| Field        | Value                                               |
| ------------ | --------------------------------------------------- |
| **Username** | `admin`                                             |
| **Password** | `admin123` _(or value of `ADMIN_PASSWORD` env var)_ |

### Student Accounts

- **Self-Registration**: Students register at `/register` with email OTP verification.
- **Bulk Upload**: Admin can upload a CSV/Excel file with student data.

---

## 📂 Project Structure

```
Plan-Bendora/
│
├── app.py                  # Main application — routes, config, and server entry point
├── models.py               # SQLAlchemy models (User, Student, Course, SystemConfig, Notice)
├── allocation_engine.py    # Core FCFS allocation algorithm with analytics
├── data_processor.py       # CSV/Excel file parser with flexible column mapping
├── report_generator.py     # PDF & Excel report generation
├── requirements.txt        # Python dependencies (pinned versions)
│
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore rules
│
├── static/                 # Static assets
│   ├── index.css           # Custom Glassmorphism CSS design system
│   ├── script.js           # Client-side JavaScript
│   ├── clg_logo_nobg.png   # College logo (transparent)
│   └── login_banner.png    # Login page banner image
│
├── templates/              # Jinja2 HTML templates
│   ├── login.html          # Login page
│   ├── register.html       # Student registration with OTP
│   ├── admin_dashboard.html    # Admin control panel
│   ├── admin_students.html     # Student list management
│   ├── admin_results.html      # Allocation results & analytics
│   ├── edit_student.html       # Edit student profile
│   ├── edit_course.html        # Edit course details
│   └── student_dashboard.html  # Student preference & status view
│
├── instance/               # SQLite database (auto-generated)
├── uploads/                # Temporary uploaded CSV/Excel files
└── outputs/                # Generated reports (Excel & PDF)
```

---

## 🌐 API Routes Overview

### Authentication

| Method     | Route               | Description                                      |
| ---------- | ------------------- | ------------------------------------------------ |
| `GET/POST` | `/login`            | Student/Admin login (supports email or username) |
| `GET/POST` | `/register`         | Student self-registration with OTP               |
| `POST`     | `/send_otp`         | Send OTP to student email (rate-limited: 50/hr)  |
| `POST`     | `/verify_otp_async` | Verify OTP asynchronously                        |
| `POST`     | `/logout`           | Log out current user                             |

### Student Routes

| Method | Route                 | Description                      |
| ------ | --------------------- | -------------------------------- |
| `GET`  | `/dashboard`          | Personalized student dashboard   |
| `POST` | `/submit_preferences` | Submit course preference ranking |

### Admin Routes

| Method     | Route                          | Description                           |
| ---------- | ------------------------------ | ------------------------------------- |
| `GET`      | `/dashboard`                   | Admin control panel                   |
| `POST`     | `/admin/upload_students`       | Bulk upload students via CSV/Excel    |
| `POST`     | `/admin/setup_courses`         | Add or update a course                |
| `GET/POST` | `/admin/student/edit/<id>`     | Edit student details                  |
| `POST`     | `/admin/student/delete/<id>`   | Delete a student                      |
| `GET/POST` | `/admin/course/edit/<id>`      | Edit course details                   |
| `POST`     | `/admin/course/delete/<id>`    | Delete a course                       |
| `POST`     | `/admin/run_allocation`        | Execute the allocation algorithm      |
| `GET`      | `/admin/results`               | View allocation results & analytics   |
| `GET`      | `/download/<type>`             | Download report (`excel` or `pdf`)    |
| `GET`      | `/admin/export_course/<id>`    | Export per-course student list        |
| `POST`     | `/admin/toggle_repref`         | Toggle preference re-submission       |
| `POST`     | `/admin/set_allocation_window` | Set preference submission time window |
| `POST`     | `/admin/add_notice`            | Publish a notice                      |
| `POST`     | `/admin/delete_notice/<id>`    | Delete a notice                       |
| `POST`     | `/admin/reset_data`            | Reset all students & courses          |

---

## 🧠 How the Allocation Algorithm Works

```
1. Students are SORTED by submission_time (ascending) — earliest first.
   → Students who submit `NULL` timestamps are sorted to the end.

2. For each student (in priority order):
   a. Iterate through their preference list (Pref 1 → Pref 8).
   b. Check if the preferred course has available capacity.
   c. If YES → Allocate the student to that course. Mark as "Allocated".
   d. If NO  → Move to the next preference.

3. If NO preferences can be fulfilled → Mark the student as "Unassigned".

4. Generate analytics: satisfaction rate, course occupancy, faculty distribution.
```

> **Fairness Guarantee**: The strict FCFS ordering ensures students who submit earlier always get priority, regardless of other factors.

---

## 📊 CSV/Excel Upload Format

The system supports **flexible column mapping**. The data processor automatically recognizes these column header formats:

### Student Data

| Standard Header                 | Also Accepts                                                                |
| ------------------------------- | --------------------------------------------------------------------------- |
| `Student ID`                    | `Roll No.`, `Unique ID`                                                     |
| `Name`                          | `Name of the student`, `Student Name`                                       |
| `Preference 1` – `Preference 8` | `Open Elective Choices [Priority No. 1]` – `[Priority No. 8]`               |
| _(fallback)_                    | `Mandatory Non Credit Course Choices [Priority No. 1]` – `[Priority No. 8]` |

### Minimum Required Columns

- `Student ID`
- `Name`
- `Preference 1`

---

## ⚠️ Troubleshooting

| Problem                        | Solution                                                                         |
| ------------------------------ | -------------------------------------------------------------------------------- |
| **`Command not found: flask`** | Ensure your virtual environment is activated. Try: `python -m flask init-db`     |
| **Database/schema errors**     | Delete the `instance/` folder and run `flask init-db` again to start fresh.      |
| **File upload fails**          | Check that your CSV/Excel headers match the expected format (see above).         |
| **OTP not sending**            | Verify `BREVO_API_KEY` and `MAIL_USERNAME` are set correctly in `.env`.          |
| **`ModuleNotFoundError`**      | Run `pip install -r requirements.txt` inside your activated virtual environment. |
| **Port already in use**        | Use `python app.py` on a different port, or kill the existing process.           |

---

## 🤝 Contributing

Contributions are welcome! Here's how:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

---

## 📝 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/Shubham00043">Shubham</a>
</p>
#   P l a n - B e n d o r a
