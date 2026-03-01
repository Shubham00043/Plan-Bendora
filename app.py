from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import secrets
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import string
from werkzeug.utils import secure_filename
import os
import urllib.request
import json
from io import BytesIO, StringIO
import pandas as pd
from models import db, User, Student, Course, SystemConfig, Notice
from data_processor import DataProcessor
from allocation_engine import AllocationEngine
from report_generator import ReportGenerator
from datetime import datetime
from flask_wtf.csrf import CSRFProtect
import logging
import os
from dotenv import load_dotenv
import re

# Automatically load .env file from the same directory as app.py
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'), override=True)

app = Flask(__name__)

# Security: Load secret key from environment or generate a secure one for development
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('FLASK_DEBUG') == '1':
        app.config['SECRET_KEY'] = 'dev-key-secure-in-prod'
    else:
        # Generate a random one if missing in prod (safer than hardcoded)
        app.config['SECRET_KEY'] = os.urandom(24).hex()

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    db_url = 'sqlite:///smart_allocation.db'
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.getcwd(), 'outputs')

csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["500 per day", "50 per hour"])

# Sender Configuration for Brevo API
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME') # Used as sender email
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'success': False, 'message': f"Rate limit exceeded: {e.description}"}), 429

# --- Auth Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form.get('username')
        password = request.form.get('password')
        
        # Try finding by username first
        user = User.query.filter_by(username=login_input).first()
        
        # If not found, check if it's an email in the Student table
        if not user:
            student = Student.query.filter_by(email=login_input).first()
            if student:
                user = User.query.filter_by(username=student.student_id).first()
                
        if user and user.verify_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/send_otp', methods=['POST'])
@limiter.limit("50 per hour")
def send_otp():
    email = request.json.get('email')
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'}), 400

    if not re.match(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$', email.lower()):
        return jsonify({'success': False, 'message': 'Invalid email format'}), 400

    # Check if a user already exists with this email
    existing_student = Student.query.filter_by(email=email.lower()).first()
    if existing_student:
        return jsonify({'success': False, 'message': 'User already exists with this email. Please Login.'}), 400

    otp = ''.join(secrets.choice(string.digits) for _ in range(6))
    session['registration_otp'] = otp
    session['registration_email'] = email.lower()
    session['registration_otp_ts'] = datetime.now().timestamp()
    session['registration_otp_attempts'] = 0

    brevo_key = os.environ.get('BREVO_API_KEY')
    if not brevo_key:
        return jsonify({'success': False, 'message': 'Email service not configured.'})

    try:
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": brevo_key,
            "content-type": "application/json"
        }
        sender_email = app.config.get('MAIL_USERNAME')
        # Fallback for sender if MAIL_USERNAME isn't an email
        if not sender_email or '@' not in sender_email:
            sender_email = "noreply@smartallocation.com"
            
        data = {
            "sender": {"name": "Smart Course Allocation", "email": sender_email},
            "to": [{"email": email}],
            "subject": "Your Smart Course Allocation Registration OTP",
            "htmlContent": f"Hello,<br><br>Your Verification OTP code is: <strong style='font-size:1.5em'>{otp}</strong><br><br>Do not share this code with anyone.<br>If you did not request this, you can ignore this email."
        }
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status in (200, 201, 202):
                return jsonify({'success': True, 'message': 'OTP sent successfully'})
            else:
                app.logger.error(f"Brevo API returned status: {response.status}")
                return jsonify({'success': False, 'message': 'Failed to send OTP'})
    except Exception as e:
        app.logger.exception(f"Brevo API failed: {e}")
        return jsonify({'success': False, 'message': 'Failed to send OTP. Please try again later.'})
    
@app.route('/verify_otp_async', methods=['POST'])
def verify_otp_async():
    email = request.json.get('email')
    otp_input = request.json.get('otp')
    
    session_otp = session.get('registration_otp')
    session_email = session.get('registration_email')
    otp_ts = session.get('registration_otp_ts', 0)
    attempts = session.get('registration_otp_attempts', 0)
    
    if not email or not otp_input:
        return jsonify({'success': False, 'message': 'Email and OTP are required'}), 400

    if attempts >= 5:
        session.pop('registration_otp', None)
        return jsonify({'success': False, 'message': 'Maximum attempts exceeded. Please request a new OTP.'}), 429
        
    if (datetime.now().timestamp() - otp_ts) > 900:
        session.pop('registration_otp', None)
        return jsonify({'success': False, 'message': 'OTP has expired. Please request a new one.'}), 400
        
    if not session_otp or not session_email or email.lower() != session_email or otp_input != session_otp:
        session['registration_otp_attempts'] = attempts + 1
        if session['registration_otp_attempts'] >= 5:
            session.pop('registration_otp', None)
            return jsonify({'success': False, 'message': 'Maximum attempts exceeded. Please request a new OTP.'}), 429
        return jsonify({'success': False, 'message': 'Invalid OTP.'}), 400
        
    # Valid OTP
    session['registration_otp_verified'] = True
    session.pop('registration_otp', None)
    return jsonify({'success': True, 'message': 'Email verified successfully!'})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Sanitization
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        otp_input = request.form.get('otp', '').strip()
        student_class = request.form.get('student_class', '').strip()
        roll_no = request.form.get('roll_no', '').strip()
        mobile = request.form.get('mobile', '').strip()
        department = request.form.get('department', '').strip()
        
        # Validation
        if not all([username, password, full_name, email, otp_input, student_class, roll_no, mobile, department]):
            flash('All fields are required.', 'error')
            return render_template('register.html')

        # 1. UserID Validation
        if not re.match(r'^[a-zA-Z0-9\-_]{3,30}$', username):
            flash('UserID must be 3-30 characters long (letters, numbers).', 'error')
            return render_template('register.html')
            
        if not (1 <= len(roll_no) <= 10):
            flash('Roll number must be between 1 and 10 characters.', 'error')
            return render_template('register.html')

        # 2. Password Strength
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html')
            
        # 3. Mobile Validation
        if not re.match(r'^\d{10}$', mobile):
            flash('Mobile number must be exactly 10 digits.', 'error')
            return render_template('register.html')

        # 4. Email Validation (Stricter)
        if not re.match(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$', email):
           flash('Invalid email address format.', 'error')
           return render_template('register.html')
           
        # 4.5. OTP Validation
        is_verified = session.get('registration_otp_verified')
        session_email = session.get('registration_email')
        
        if not is_verified or not session_email or email != session_email:
            flash('Invalid or expired OTP. Please verify your email again.', 'error')
            return render_template('register.html')

        # 5. Full Name Validation
        if not re.match(r'^[a-zA-Z\s]+$', full_name) or len(full_name) < 3 or len(full_name) > 30:
            flash('Full name must contain only letters and spaces (3-30 chars).', 'error')
            return render_template('register.html')

        # 6. Allowed Values
        allowed_classes = ['FY', 'SY', 'TY', 'Final Year']
        if student_class not in allowed_classes:
            flash('Invalid class selection.', 'error')
            return render_template('register.html')
            
        allowed_departments = [
            "Agricultural Engineering", "Computer Science Engineering", "Civil Engineering",
            "Computer Science Design", "Electronics and Computer Engineering", 
            "Artificial Intelligence and Data Science", "Mechanical Engineering", 
            "Electrical Engineering", "Mechatronics Engineering", 
            "Plastics and Polymer Engineering", "Electronics and Telecommunication Engineering", 
            "Information Technology"
        ]
        if department not in allowed_departments:
            flash('Invalid department selection.', 'error')
            return render_template('register.html')
        
        # Security: Prevent privilege escalation by ignoring 'role' from form
        role = 'student' # Default role
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('UserID already exists', 'error')
        else:
            # 1. Create User Login
            new_user = User(username=username, role=role)
            new_user.password = password
            db.session.add(new_user)
            
            # 2. Create Student Profile
            # Check if student record exists (e.g. from bulk upload)
            student = Student.query.filter_by(student_id=username).first()
            
            if student:
                # Update existing record with registration details
                student.name = full_name
                student.email = email
                student.student_class = student_class
                student.roll_no = roll_no
                student.mobile_no = mobile
                student.department = department
            else:
                # Create new student record
                new_student = Student(
                    student_id=username,
                    name=full_name,
                    email=email,
                    student_class=student_class,
                    roll_no=roll_no,
                    mobile_no=mobile,
                    department=department
                )
                db.session.add(new_student)
            
            db.session.commit()
            session.pop('registration_otp', None)
            session.pop('registration_email', None)
            session.pop('registration_otp_verified', None)
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Helpers ---
def get_config(key, default=None):
    cfg = SystemConfig.query.filter_by(key=key).first()
    return cfg.value if cfg else default

def set_config(key, value):
    cfg = SystemConfig.query.filter_by(key=key).first()
    if not cfg:
        cfg = SystemConfig(key=key, value=str(value))
        db.session.add(cfg)
    else:
        cfg.value = str(value)
    db.session.commit()

# --- Main App Routes ---
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    allow_repref = get_config('allow_repref', 'false').lower() == 'true'
    notices = Notice.query.order_by(Notice.created_at.desc()).all()
    
    allocation_start = get_config('allocation_start', '')
    allocation_end = get_config('allocation_end', '')

    if current_user.role == 'admin':
        students = Student.query.all()
        courses = Course.query.all()
        return render_template('admin_dashboard.html', 
                               students=students, 
                               courses=courses, 
                               allow_repref=allow_repref,
                               notices=notices,
                               allocation_start=allocation_start,
                               allocation_end=allocation_end)
    else:
        student_record = Student.query.filter_by(student_id=current_user.username).first()
        courses = Course.query.all()
        recommendations = student_record.get_recommendations() if student_record else []
        
        # Check time window
        now = datetime.now()
        out_of_window = False
        window_message = None
        window_state = 'open' # Default
        
        try:
            if allocation_start:
                start_dt = datetime.fromisoformat(allocation_start)
                if now < start_dt:
                    out_of_window = True
                    window_state = 'upcoming'
                    window_message = f"Preference window opens: {start_dt.strftime('%d %b %Y, %I:%M %p')}"
            
            if allocation_end:
                end_dt = datetime.fromisoformat(allocation_end)
                if now > end_dt:
                    out_of_window = True
                    window_state = 'closed'
                    window_message = f"Preference window closed: {end_dt.strftime('%d %b %Y, %I:%M %p')}"
                elif not out_of_window:
                    window_message = f"Window closes: {end_dt.strftime('%d %b %Y, %I:%M %p')}"
        except ValueError:
            pass # Invalid format

        # Check if they can still submit
        already_submitted = student_record and student_record.preferences
        can_submit = (not already_submitted or allow_repref) and not out_of_window
        
        # Number of preference slots = min(available courses, 8)
        num_preferences = min(len(courses), 8)
        
        # Limit to latest 3 notices for students
        student_notices = notices[:3]
        
        return render_template('student_dashboard.html', 
                               student=student_record, 
                               courses=courses,
                               recommendations=recommendations,
                               can_submit=can_submit,
                               num_preferences=num_preferences,
                               notices=student_notices,
                               window_message=window_message,
                               window_state=window_state,
                               allocation_start=allocation_start,
                               allocation_end=allocation_end,
                               now=now.isoformat())

@app.route('/submit_preferences', methods=['POST'])
@login_required
def submit_preferences():
    if current_user.role != 'student':
        return "Unauthorized", 403
    
    student = Student.query.filter_by(student_id=current_user.username).first()
    allow_repref = get_config('allow_repref', 'false').lower() == 'true'
    
    if student and student.preferences and not allow_repref:
        flash('Preference re-submission is currently disabled.', 'error')
        return redirect(url_for('dashboard'))

    # Time window validation
    allocation_start = get_config('allocation_start', '')
    allocation_end = get_config('allocation_end', '')
    now = datetime.now()
    try:
        if allocation_start and now < datetime.fromisoformat(allocation_start):
            flash('Preference selection has not started yet.', 'error')
            return redirect(url_for('dashboard'))
        if allocation_end and now > datetime.fromisoformat(allocation_end):
            flash('Preference selection window has closed.', 'error')
            return redirect(url_for('dashboard'))
    except ValueError:
        pass

    prefs = request.form.getlist('preferences')
    
    # Validate: all preference slots must be filled (not empty)
    courses = Course.query.all()
    expected_count = min(len(courses), 8)
    # Remove any empty values
    prefs = [p for p in prefs if p.strip()]
    if len(prefs) < expected_count:
        flash(f'All {expected_count} preference fields are required. Please fill every slot.', 'error')
        return redirect(url_for('dashboard'))
    
    # Update or Create Student Record
    student = Student.query.filter_by(student_id=current_user.username).first()
    if not student:
        student = Student(student_id=current_user.username, name=current_user.username)
        db.session.add(student)
    
    student.preferences = prefs
    student.submission_time = datetime.now() 
    db.session.commit()
    flash('Preferences submitted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/students')
@login_required
def admin_students_list():
    if current_user.role != 'admin':
        return "Unauthorized", 403
    
    students = Student.query.all()
    return render_template('admin_students.html', students=students)

@app.route('/admin/student/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_student(id):
    if current_user.role != 'admin':
        return "Unauthorized", 403
        
    student = Student.query.get_or_404(id)
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        student_class = request.form.get('student_class')
        roll_no = request.form.get('roll_no')
        mobile = request.form.get('mobile')
        department = request.form.get('department')
        
        # Validation (mirrors register)
        if not all([full_name, email, student_class, roll_no, mobile, department]):
            flash('All fields are required.', 'error')
            return render_template('edit_student.html', student=student)

        if not re.match(r'^\d{10}$', mobile):
            flash('Mobile number must be exactly 10 digits.', 'error')
            return render_template('edit_student.html', student=student)

        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
           flash('Invalid email address format.', 'error')
           return render_template('edit_student.html', student=student)

        # Check for unique email across other students
        existing_email_student = Student.query.filter_by(email=email).first()
        if existing_email_student and existing_email_student.id != student.id:
            flash('Email already registered to another student.', 'error')
            return render_template('edit_student.html', student=student)

        student.name = full_name
        student.email = email
        student.student_class = student_class
        student.roll_no = roll_no
        student.mobile_no = mobile
        student.department = department
        
        try:
            db.session.commit()
            flash('Student updated successfully!', 'success')
            return redirect(url_for('admin_students_list'))
        except Exception as e:
            db.session.rollback()
            app.logger.exception("Error updating student")
            flash('Error updating student, please try again.', 'error')
            
    return render_template('edit_student.html', student=student)

@app.route('/admin/student/delete/<int:id>', methods=['POST'])
@login_required
def delete_student(id):
    if current_user.role != 'admin':
        return "Unauthorized", 403
        
    student = Student.query.get_or_404(id)
    try:
        # Check if student has a linked User account and delete it too
        user = User.query.filter_by(username=student.student_id).first()
        if user:
            db.session.delete(user)
            
        db.session.delete(student)
        db.session.commit()
        flash('Student deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.exception("Error deleting student")
        flash('An error occurred while deleting the student.', 'error')
        
    return redirect(url_for('admin_students_list'))

@app.route('/admin/course/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_course(id):
    if current_user.role != 'admin':
        return "Unauthorized", 403
        
    course = Course.query.get_or_404(id)
    
    if request.method == 'POST':
        course.name = request.form.get('name')
        
        cap_raw = request.form.get('capacity')
        if cap_raw:
            try:
                cap = int(cap_raw)
                if cap < 1: 
                    raise ValueError("Capacity must be >= 1")
                course.capacity = cap
            except ValueError:
                flash('Invalid capacity value', 'error')
                return render_template('edit_course.html', course=course)
            
        try:
            db.session.commit()
            flash('Course updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            app.logger.exception("Error updating course")
            flash('An error occurred updating the course. Please try again or contact support.', 'error')
            
    return render_template('edit_course.html', course=course)

@app.route('/admin/course/delete/<int:id>', methods=['POST'])
@login_required
def delete_course(id):
    if current_user.role != 'admin':
        return "Unauthorized", 403
        
    course = Course.query.get_or_404(id)
    try:
        db.session.delete(course)
        db.session.commit()
        flash('Course deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting course: {str(e)}', 'error')
        
    return redirect(url_for('dashboard'))

@app.route('/admin/upload_students', methods=['POST'])
@login_required
def upload_students():
    if current_user.role != 'admin':
        return "Unauthorized", 403
    
    file = request.files.get('file')
    if file:
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        
        try:
            df, _ = DataProcessor.process_file(path)
            for _, row in df.iterrows():
                # Check if student already exists
                student = Student.query.filter_by(student_id=str(row['Student ID'])).first()
                if not student:
                    student = Student(student_id=str(row['Student ID']), name=row['Name'])
                    db.session.add(student)
                
                student.name = row['Name']
                # Collect all preference columns
                prefs = [row[f'Preference {i}'] for i in range(1, 9) if f'Preference {i}' in row and pd.notna(row[f'Preference {i}'])]
                student.preferences = prefs
                
            db.session.commit()
            flash('Students imported successfully!', 'success')
        except Exception:
            logging.exception("Error during student upload")
            flash('Unable to complete the student import. Please check the file format.', 'error')
            
    return redirect(url_for('dashboard'))

@app.route('/admin/setup_courses', methods=['POST'])
@login_required
def setup_courses():
    if current_user.role != 'admin':
        return "Unauthorized", 403
    
    name = request.form.get('name')
    cap_raw = request.form.get('capacity')
    
    if not name or not cap_raw:
        flash('Course name and capacity are required.', 'error')
        return redirect(url_for('dashboard'))
        
    try:
        cap = int(cap_raw)
        if cap < 1:
            raise ValueError("Capacity must be at least 1")
    except (ValueError, TypeError):
        flash('Invalid capacity value. Must be a positive integer.', 'error')
        return redirect(url_for('dashboard'))
    
    course = Course.query.filter_by(name=name).first()
    
    if not course:
        course = Course(name=name, capacity=cap)
        db.session.add(course)
    else:
        course.capacity = cap
    
    db.session.commit()
    flash(f'Course {name} updated/added.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/add_notice', methods=['POST'])
@login_required
def add_notice():
    if current_user.role != 'admin':
        return "Unauthorized", 403
    
    title = request.form.get('title')
    content = request.form.get('content')
    notice_type = request.form.get('type', 'info')
    
    if not title or not content:
        flash('Title and content are required.', 'error')
        return redirect(url_for('dashboard'))
        
    notice = Notice(title=title, content=content, type=notice_type)
    db.session.add(notice)
    db.session.commit()
    flash('Notice added successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/delete_notice/<int:id>', methods=['POST'])
@login_required
def delete_notice(id):
    if current_user.role != 'admin':
        return "Unauthorized", 403
    
    notice = db.session.get(Notice, id)
    if notice:
        db.session.delete(notice)
        db.session.commit()
        flash('Notice deleted.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/run_allocation', methods=['POST'])
@login_required
def run_allocation():
    if current_user.role != 'admin':
        return "Unauthorized", 403
    
    students = Student.query.all()
    courses = Course.query.all()
    
    try:
        engine = AllocationEngine(students, courses)
        results = engine.allocate()
        db.session.commit() # Save allocations to DB
        
        # Generate reports
        summary = engine.get_analytics()
        ReportGenerator.generate_excel(results, os.path.join(app.config['OUTPUT_FOLDER'], 'results.xlsx'))
        ReportGenerator.generate_pdf(results, summary, os.path.join(app.config['OUTPUT_FOLDER'], 'report.pdf'))
        
        flash('Allocation optimized and completed!', 'success')
    except Exception:
        logging.exception("Error during allocation engine run")
        flash('An error occurred during allocation processing.', 'error')
        
    return redirect(url_for('admin_results'))

@app.route('/admin/results')
@login_required
def admin_results():
    if current_user.role != 'admin':
        return "Unauthorized", 403
    
    students = Student.query.all()
    courses = Course.query.all()
    engine = AllocationEngine(students, courses)
    analytics = engine.get_analytics()
    
    return render_template('admin_results.html', students=students, analytics=analytics, courses=courses)

@app.route('/download/<type>')
@login_required
def download_file(type):
    if current_user.role != 'admin':
        return "Unauthorized", 403
        
    if type == 'excel':
        filename = 'results.xlsx'
    elif type == 'pdf':
        filename = 'report.pdf'
    else:
        return "Invalid download type", 400
        
    path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "File not found. Please run allocation first.", 404

@app.route('/admin/toggle_repref', methods=['POST'])
@login_required
def toggle_repref():
    if current_user.role != 'admin':
        return "Unauthorized", 403
    
    current_val = get_config('allow_repref', 'false')
    new_val = 'true' if current_val == 'false' else 'false'
    set_config('allow_repref', new_val)
    
    status = "enabled" if new_val == 'true' else "disabled"
    flash(f'Student re-preference {status}!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/set_allocation_window', methods=['POST'])
@login_required
def set_allocation_window():
    if current_user.role != 'admin':
        return "Unauthorized", 403
    
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    
    set_config('allocation_start', start_time if start_time else '')
    set_config('allocation_end', end_time if end_time else '')
    
    flash('Allocation time window updated!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/reset_data', methods=['POST'])
@login_required
def reset_data():
    if current_user.role != 'admin':
        return "Unauthorized", 403
    
    if request.form.get('confirm') != 'yes':
        flash('Reset cancelled. You must confirm to proceed.', 'error')
        return redirect(url_for('dashboard'))

    try:
        # Delete students and courses
        # We keep Users (accounts) but reset their roles' data
        Student.query.delete()
        Course.query.delete()
        db.session.commit()
        
        # Also delete generated reports
        for f in ['results.xlsx', 'report.pdf']:
            path = os.path.join(app.config['OUTPUT_FOLDER'], f)
            if os.path.exists(path): os.remove(path)
            
        flash('All system data (Students & Courses) has been reset.', 'success')
    except Exception:
        logging.exception("Error during system reset")
        flash('An error occurred during system reset.', 'error')
        
    return redirect(url_for('dashboard'))

@app.cli.command("init-db")
def init_db_command():
    """Clear existing data and create new tables."""
    db.create_all()
    
    # Use environment provided password if available
    admin_pass = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role='admin')
        admin.password = admin_pass
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user created with username 'admin'")
    else:
        print("Admin user already exists.")
        
    if not SystemConfig.query.filter_by(key='allow_repref').first():
        config = SystemConfig(key='allow_repref', value='false')
        db.session.add(config)
        db.session.commit()
        print("Default system configuration initialized.")
    
    print("Database initialized successfully.")

@app.route('/admin/export_course/<int:course_id>')
@login_required
def export_course_data(course_id):
    if current_user.role != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))

    course = Course.query.get(course_id)
    if not course:
        flash('Course not found.', 'error')
        return redirect(url_for('admin_results'))

    # Fetch students allocated to this course
    students = Student.query.filter_by(allocated_course_id=course.id).all()
    
    if not students:
        flash(f'No students allocated to {course.name}.', 'warning')
        return redirect(url_for('admin_results'))

    # Create CSV data
    data = []
    for s in students:
        data.append({
            'Student ID': s.student_id,
            'Name': s.name,
            'Department': s.department,
            'Class': s.student_class,
            'Roll No': s.roll_no,
            'Mobile': s.mobile_no,
            'Email': s.email,
            'Submission Time': s.submission_time.strftime('%Y-%m-%d %H:%M:%S') if s.submission_time else 'N/A'
        })
    
    df = pd.DataFrame(data)
    
    # Generate response
    output = StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return send_file(
        BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'{course.name.replace(" ", "_")}_Allocations.csv'
    )

if __name__ == "__main__":
    # Check if we are in development mode (default to true for local run)
    if os.environ.get('FLASK_ENV', 'development') == 'development':
        try:
            from livereload import Server
            server = Server(app.wsgi_app)
            # Watch templates and static files for changes
            server.watch('templates/*.html')
            server.watch('static/*.css')
            server.watch('static/*.js')
            print("🚀 Starting development server with LiveReload on http://127.0.0.1:5000")
            server.serve(port=5000, debug=True)
        except ImportError:
            print("⚠️ LiveReload not installed. Falling back to standard Flask runner.")
            print("💡 Tip: Run 'pip install livereload' for auto-browser refreshing.")
            app.run(debug=True)
    else:
        # Production mode
        app.run(debug=False, host='0.0.0.0')
