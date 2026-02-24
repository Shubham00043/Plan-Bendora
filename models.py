from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    _password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='student') # 'admin' or 'student'

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self._password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self._password_hash, password)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    enrolled_count = db.Column(db.Integer, default=0)
    faculty_name = db.Column(db.String(150))

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True)

    submission_time = db.Column(db.DateTime, nullable=True)
    
    # Store preferences as a JSON or a related table
    preferences = db.Column(db.JSON) # List of course names in order
    
    allocated_course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    allocation_status = db.Column(db.String(50), default='Pending') # Pending, Allocated, Unassigned
    
    allocated_course = db.relationship('Course', backref='assigned_students')

    # Additional details for admin view
    student_class = db.Column(db.String(50))
    roll_no = db.Column(db.String(50))
    mobile_no = db.Column(db.String(20))
    department = db.Column(db.String(100))

    def get_recommendations(self):
        """Simple rule-based recommendation logic."""
        all_courses = Course.query.all()
        recs = []
        
        # Balance logic: Recommend available courses with most seats left
        available_courses = [c for c in all_courses if c.enrolled_count < c.capacity]
        if available_courses:
            sorted_available = sorted(available_courses, key=lambda x: (x.capacity - x.enrolled_count), reverse=True)
            recs = [c.name for c in sorted_available[:2]]
            
        return recs[:3]

class SystemConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(100))

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='info') # 'deadline', 'maintenance', 'info'
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
