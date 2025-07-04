import os
import re
import pandas as pd
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from bson import ObjectId
from collections import defaultdict

# Import from extensions.py and other modules
from extensions import mongo
from models import User
from forms import LoginForm, SignUpForm, FileUploadForm, ConstraintForm, TimeSettingsForm
from genetic_algorithm import run_genetic_algorithm, parse_time, timeslot_to_numeric

# Create a Blueprint
main_bp = Blueprint('main', __name__)

# --- Master lists for Days and Timeslots ---
DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
# This is now the base list of all possible slots in a day
TIME_SLOTS = [
    '10:00-11:00',
    '11:00-12:00',
    '12:00-13:00',
    '13:00-14:00',
    '14:00-15:00',
    '15:00-16:00',
    '16:00-16:15',
    '16:15-17:15'
]


# --- DECORATORS ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- AUTHENTICATION ROUTES ---

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.find_by_username(form.username.data)
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html', title='Login', form=form)

@main_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = SignUpForm()
    if form.validate_on_submit():
        existing_user = User.find_by_username(form.username.data)
        if existing_user:
            flash('That username is already taken. Please choose a different one.', 'danger')
            return render_template('signup.html', title='Sign Up', form=form)

        hashed_password = generate_password_hash(form.password.data)
        mongo.db.users.insert_one({
            'username': form.username.data,
            'password': hashed_password,
            'role': 'user'
        })
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('main.login'))
    return render_template('signup.html', title='Sign Up', form=form)

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

# --- DASHBOARD ROUTES ---

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Remove the automatic redirect to admin panel for admins
    # Let both admin and regular users see the dashboard
    
    timetable_data = list(mongo.db.timetable.find())
    
    # Since only one lecture can be in a slot, we no longer need a list
    schedule = {day: {ts: None for ts in TIME_SLOTS} for day in DAYS_OF_WEEK}
    for entry in timetable_data:
        if entry.get('day') in schedule and entry.get('timeslot') in schedule[entry.get('day')]:
            schedule[entry['day']][entry['timeslot']] = entry

    return render_template('dashboard.html', title='Dashboard',
                           schedule=schedule, days=DAYS_OF_WEEK, timeslots=TIME_SLOTS)


# --- ADMIN PANEL ROUTES ---
@main_bp.route('/admin')
@login_required
@admin_required
def admin_panel():
    upload_form = FileUploadForm()
    constraint_form = ConstraintForm()
    settings_form = TimeSettingsForm()

    # Fetch break time settings to pre-populate the form
    settings = mongo.db.settings.find_one({'name': 'breaks'})
    if settings:
        settings_form.lunch_start_time.data = settings.get('lunch_start_time')
        settings_form.lunch_end_time.data = settings.get('lunch_end_time')
        settings_form.recess_start_time.data = settings.get('recess_start_time')
        settings_form.recess_end_time.data = settings.get('recess_end_time')
    else:
        # Default values if nothing is in the database
        settings_form.lunch_start_time.data = '13:00'
        settings_form.lunch_end_time.data = '14:00'
        settings_form.recess_start_time.data = '16:00'
        settings_form.recess_end_time.data = '16:15'

    professors = list(mongo.db.professors.find())
    constraints_data = list(mongo.db.constraints.find())
    
    relations_data = list(mongo.db.required_lectures.find())
    prof_subject_map = defaultdict(lambda: defaultdict(int))
    for rel in relations_data:
        prof_subject_map[rel['professor_name']][rel['subject_name']] += 1
    sorted_prof_subject_map = dict(sorted(prof_subject_map.items()))

    constraint_form.professor.choices = [(str(p['_id']), p['name']) for p in professors]

    return render_template('admin.html', title='Admin Panel',
                           upload_form=upload_form, 
                           constraint_form=constraint_form,
                           settings_form=settings_form,
                           prof_subject_map=sorted_prof_subject_map,
                           constraints=constraints_data)

@main_bp.route('/admin/settings', methods=['POST'])
@login_required
@admin_required
def update_settings():
    form = TimeSettingsForm()
    if form.validate_on_submit():
        mongo.db.settings.update_one(
            {'name': 'breaks'},
            {'$set': {
                'lunch_start_time': form.lunch_start_time.data,
                'lunch_end_time': form.lunch_end_time.data,
                'recess_start_time': form.recess_start_time.data,
                'recess_end_time': form.recess_end_time.data
            }},
            upsert=True
        )
        flash('Break time settings have been updated!', 'success')
    else:
        flash('There was an error in the time format.', 'danger')
    return redirect(url_for('main.admin_panel'))


@main_bp.route('/admin/upload', methods=['POST'])
@login_required
@admin_required
def upload_timetable():
    form = FileUploadForm()
    if form.validate_on_submit():
        # Clear all previous data
        mongo.db.professors.delete_many({})
        mongo.db.subjects.delete_many({})
        mongo.db.required_lectures.delete_many({})
        mongo.db.constraints.delete_many({})
        mongo.db.timetable.delete_many({})
        
        try:
            f = form.file.data
            filepath = os.path.join(current_app.root_path, 'uploads', secure_filename(f.filename))
            f.save(filepath)

            df = pd.read_excel(filepath, header=None)
            
            lectures_to_add = []
            
            for _, row in df.iterrows():
                for _, cell_value in enumerate(row):
                    if pd.isna(cell_value) or not isinstance(cell_value, str):
                        continue
                    
                    match = re.search(r'([A-Z\s]+Lab|[A-Z\d\s]+)\s*\((.*?)\)', cell_value, re.IGNORECASE)
                    
                    if match:
                        subject_name = match.group(1).strip()
                        prof_name = match.group(2).strip()
                        
                        # --- CHANGE: ADD DURATION FOR LECTURES ---
                        is_lab = 'lab' in subject_name.lower()
                        
                        lectures_to_add.append({
                            "subject_name": subject_name,
                            "professor_name": prof_name,
                            "duration": 2 if is_lab else 1
                        })
                        
                        mongo.db.professors.update_one({'name': prof_name}, {'$setOnInsert': {'name': prof_name}}, upsert=True)
                        mongo.db.subjects.update_one({'name': subject_name}, {'$setOnInsert': {'name': subject_name}}, upsert=True)

            if not lectures_to_add:
                flash('No valid lectures found. Please check the Excel file format.', 'warning')
            else:
                mongo.db.required_lectures.insert_many(lectures_to_add)
                flash(f'Successfully extracted {len(lectures_to_add)} total lectures/labs!', 'success')

        except Exception as e:
            flash(f'An error occurred while processing the file: {e}', 'danger')
    
    return redirect(url_for('main.admin_panel'))


@main_bp.route('/admin/constraints', methods=['POST'])
@login_required
@admin_required
def add_constraint():
    form = ConstraintForm()
    professors = list(mongo.db.professors.find())
    form.professor.choices = [(str(p['_id']), p['name']) for p in professors]

    if form.validate_on_submit():
        prof = mongo.db.professors.find_one({'_id': ObjectId(form.professor.data)})
        
        if prof:
            mongo.db.constraints.insert_one({
                'professor_name': prof['name'],
                'day': form.day.data,
                'start_time': form.start_time.data,
                'end_time': form.end_time.data
            })
            flash('Constraint added successfully!', 'success')
        else:
            flash('Professor not found.', 'danger')
            
    return redirect(url_for('main.admin_panel'))

@main_bp.route('/admin/generate')
@login_required
@admin_required
def generate_new_timetable():
    flash('Generating timetable...', 'info')
    
    try:
        mongo.db.timetable.delete_many({})
        required_lectures = list(mongo.db.required_lectures.find())
        constraints = list(mongo.db.constraints.find())

        if not required_lectures:
            flash('Cannot generate timetable. Please upload lectures first.', 'danger')
            return redirect(url_for('main.admin_panel'))

        settings = mongo.db.settings.find_one({'name': 'breaks'}) or {}
        lunch_start = parse_time(settings.get('lunch_start_time', '13:00'))
        lunch_end = parse_time(settings.get('lunch_end_time', '14:00'))
        recess_start = parse_time(settings.get('recess_start_time', '16:00'))
        recess_end = parse_time(settings.get('recess_end_time', '16:15'))

        schedulable_slots = []
        for slot_str in TIME_SLOTS:
            slot_start, slot_end = timeslot_to_numeric(slot_str)
            if slot_end - slot_start != 60: continue # Only consider 1-hour base slots for scheduling
            
            is_in_lunch = max(slot_start, lunch_start) < min(slot_end, lunch_end)
            is_in_recess = max(slot_start, recess_start) < min(slot_end, recess_end)

            if not is_in_lunch and not is_in_recess:
                schedulable_slots.append(slot_str)
        
        # The new GA handles all complex logic internally
        fittest_timetable = run_genetic_algorithm(required_lectures, constraints, schedulable_slots, DAYS_OF_WEEK)
        
        if not fittest_timetable:
            flash('Could not generate a valid timetable. The constraints may be too strict or there are not enough available slots for all lectures.', 'danger')
        else:
            mongo.db.timetable.insert_many(fittest_timetable)
            flash('New timetable generated successfully!', 'success')

    except ValueError as e:
        flash(f'Error: {e}', 'danger')
    except Exception as e:
        flash(f'An unexpected error occurred during generation: {e}', 'danger')

    return redirect(url_for('main.admin_panel'))