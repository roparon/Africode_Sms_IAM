from flask import Flask, render_template, request, redirect, url_for, flash
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required, current_user, roles_required, hash_password
from flask_sqlalchemy import SQLAlchemy
from flask_mailman import Mail
from flask_bootstrap import Bootstrap5
from werkzeug.security import generate_password_hash
from flask_security import roles_required
from flask_wtf.csrf import CSRFProtect
import config

app = Flask(__name__)
Bootstrap5(app)
app.config.from_object(config)
db = SQLAlchemy(app)

roles_users = db.Table('roles_users',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean(), default=True)
    fs_uniquifier = db.Column(db.String(255), unique=True)
    confirmed_at = db.Column(db.DateTime)
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))
    webauthn = db.relationship('WebAuth', backref='user', uselist=False)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)

class WebAuth(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    teacher = db.relationship('User', backref='courses_taught')
    enrollments = db.relationship('Enrollment', backref='course', lazy=True)

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    grade = db.Column(db.Float, nullable=True)

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

mail = Mail(app)

@app.route('/')
@login_required
def index():
    courses_count = Course.query.count()
    students_count = User.query.join(User.roles).filter(Role.name == 'Students').count()
    teacher_count = User.query.join(User.roles).filter(Role.name == 'Teacher').count()
    return render_template('index.html', courses_count=courses_count, students_count=students_count, teacher_count=teacher_count)

@app.route('/courses')
@login_required
def courses():
    if current_user.has_role('Admin') or current_user.has_role('Teacher'):
        courses = Course.query.all()
    else:
        courses = Course.query.all()
        #courses = [enrollment.course for enrollment in current_user.enrollments]
    return render_template('course.html', courses=courses)


@app.route('/course/<int:course_id>')
@login_required
def course_details(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template('course_details.html', course=course)


@app.route('/create_course', methods=['GET', 'POST'])
@roles_required('Admin')
def create_course():
    if request.method == 'POST':
        name = request.form.get('name')
        teacher_id = request.form.get('teacher_id')
        course = Course(name=name, teacher_id=teacher_id)
        db.session.add(course)
        db.session.commit()
        flash('Course created successfully')
        return redirect(url_for('courses'))
    
    teachers = User.query.join(User.roles).filter(Role.name=='Teacher').all()
    return render_template('create_course.html', teachers=teachers)

@app.route('/enroll/<int:course_id>', methods=['GET','POST'])
@roles_required('Student')
def enroll(course_id):
    course = Course.query.get_or_404(course_id)
    if Enrollment.query.filter_by(student_id=current_user.id, course_id=course.id).first():
        flash('You are already enrolled in this course')
        return redirect(url_for('courses'))
    else:
        enrollment = Enrollment(course_id=course_id, student_id=current_user.id, grade=None)
        db.session.add(enrollment)
        db.session.commit()
        flash('You have been enrolled successfully')
        return redirect(url_for('course_details', course_id=course_id))

@app.route('/grade/<int:enrollment_id>', methods=['GET', 'POST'])
@roles_required('Teacher')
def grade(enrollment_id):
    enrollment = Enrollment.query.get_or_404(enrollment_id)
# Check if the current user is the teacher of the course
    if enrollment.course.teacher_id != current_user.id:
        flash('You are not the teacher of this course')
        return redirect(url_for('courses'))
    
    if request.method == 'POST':
        grade = request.form.get('grade')
        if grade:
            try:
                grade_value = float(grade)
                if 0 <= grade_value <= 100:  # Example range check
                    enrollment.grade = grade_value
                    db.session.commit()
                    flash('Grade submitted successfully')
                else:
                    flash('Grade must be between 0 and 100')
            except ValueError:
                flash('Invalid grade value')
        else:
            flash('No grade provided')
    
    return redirect(url_for('course_details', course_id=enrollment.course_id))
    
@app.route('/register_student', methods=['GET', 'POST'])
@roles_required('Admin')
def register_student():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email already registered!')
        else:
            student_role = user_datastore.find_role('Student')
            hashed_password = hash_password(password)
            user_datastore.create_user(email=email, password=hashed_password, roles=[student_role])
            db.session.commit()
            flash('Student registered successfully!')
        return redirect(url_for('register_student'))
    return render_template('register_student.html')

@app.route('/grades/<int:enrollment_id>')
def view_grade(enrollment_id):
    # Logic to retrieve and display grade
    pass


@app.route('/view_grades')
@roles_required('Student')
def view_grades():
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    return render_template('view_grades.html', enrollments=enrollments)


@app.route('/manage_courses', methods=['GET', 'POST'])
@login_required
@roles_required('Admin')  # Ensure only teachers can access this route
def manage_courses():
    if request.method == 'POST':
        # Handle course creation or update
        course_id = request.form.get('course_id')
        course_name = request.form.get('course_name')
        
        if course_id:
            # Update existing course
            course = Course.query.get(course_id)
            if course:
                course.name = course_name
                db.session.commit()
                flash('Course updated successfully!', 'success')
            else:
                flash('Course not found!', 'danger')
        # else:
        #     # Create a new course
        #     new_course = Course(name=course_name, teacher_id=current_user.id)
        #     db.session.add(new_course)
        #     db.session.commit()
        #     flash('Course created successfully!', 'success')
        
        return redirect(url_for('manage_courses'))

    # GET request: Show the form for creating or updating courses
    courses = Course.query.all()
    return render_template('manage_courses.html', courses=courses)

@app.route('/delete_course/<int:course_id>', methods=['POST'])
@login_required
@roles_required('Admin')
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash('Course deleted successfully!', 'success')
    return redirect(url_for('manage_courses'))



@app.route('/go-back')
def go_back():
    return redirect(request.referrer or url_for('index'))  # Redirects to the previous page or home if referrer is None

@app.route('/admin/dashboard')
@roles_required('Admin')
def admin_dashboard():
    # Logic for the admin dashboard
    return render_template('admin_dashboard.html')




@app.route('/add_user', methods=['GET', 'POST'])
@roles_required('Admin')
def add_user():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role_name = request.form['role']

        # Check if the user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('User already exists', 'danger')
            return redirect(url_for('add_user'))

        # Create a new user
        new_user = User(
            email=email,
            password = generate_password_hash(password, method='pbkdf2:sha256')

        )

        # Assign the selected role
        role = Role.query.filter_by(name=role_name).first()
        if role:
            new_user.roles.append(role)

        # Save the user to the database
        db.session.add(new_user)
        db.session.commit()

        flash('User added successfully', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_user.html')


@app.route('/view_users')
@roles_required('Admin')  # Only allow Admins to view users
def view_users():
    users = User.query.all()  # Assuming you have a User model
    return render_template('view_users.html', users=users)


@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@roles_required('Admin')  # Ensure only Admins can edit users
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    all_roles = [role.name for role in Role.query.all()]  # List of all role names
    user_roles = [role.name for role in user.roles]  # List of user roles

    if request.method == 'POST':
        email = request.form['email']
        roles = request.form.getlist('roles')  # Get list of roles from the form
        
        user.email = email
        user.roles = [Role.query.filter_by(name=role).first() for role in roles]
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('view_users'))
    
    return render_template('edit_user.html', user=user, all_roles=all_roles, user_roles=user_roles)


@app.route('/delete_user/<int:user_id>', methods=['POST'])
@roles_required('Admin')  # If you are using roles
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User has been deleted.', 'success')
    return redirect(url_for('view_users'))



if __name__ == '__main__':
    with app.app_context():
        # Create all database tables
        db.create_all()

        # Ensure roles exist and retrieve them
        admin_role = user_datastore.find_or_create_role(name='Admin', description='Administrator')
        teacher_role = user_datastore.find_or_create_role(name='Teacher', description='Teacher')
        student_role = user_datastore.find_or_create_role(name='Student', description='Student')

        # Verify roles are created
        if not admin_role or not teacher_role or not student_role:
            raise RuntimeError('Failed to create some roles')

        # Create users
        if not user_datastore.find_user(email='aaronrop40@gmail.com'):
            hashed_password = hash_password('password')
            user_datastore.create_user(email='aaronrop40@gmail.com', password=hashed_password, roles=[user_datastore.find_role('Admin')])
            db.session.commit()

        # Create another user
        if not user_datastore.find_user(email='kipronorop69@gmail.com'):
            hashed_password = hash_password('password')
            user_datastore.create_user(email='kipronorop69@gmail.com', password=hashed_password, roles=[user_datastore.find_role('Teacher')])
            db.session.commit()

        # Create another user
        if not user_datastore.find_user(email='kips6011@gmail.com'):
            hashed_password = hash_password('password')
            user_datastore.create_user(email='kips6011@gmail.com', password=hashed_password, roles=[user_datastore.find_role('Student')])
            db.session.commit()
    
    app.run(debug=True)
