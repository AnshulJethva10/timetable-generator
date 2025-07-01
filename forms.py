from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms.validators import DataRequired, EqualTo, Regexp

class LoginForm(FlaskForm):
    """Form for user login."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class SignUpForm(FlaskForm):
    """Form for user registration."""
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Sign Up')

class FileUploadForm(FlaskForm):
    """Form for uploading the timetable file."""
    file = FileField('Excel Timetable', validators=[
        FileRequired(),
        FileAllowed(['xlsx'], 'Only .xlsx files are allowed!')
    ])
    submit = SubmitField('Upload and Extract Info')

class ConstraintForm(FlaskForm):
    """Form for setting professor availability constraints."""
    professor = SelectField('Professor', validators=[DataRequired()])
    day = SelectField('Day', choices=[
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday')
    ], validators=[DataRequired()])
    start_time = StringField('Start Time (HH:MM)', validators=[DataRequired(), Regexp(r'^\d{2}:\d{2}$', message='Format must be HH:MM')])
    end_time = StringField('End Time (HH:MM)', validators=[DataRequired(), Regexp(r'^\d{2}:\d{2}$', message='Format must be HH:MM')])
    submit = SubmitField('Add Constraint')

class TimeSettingsForm(FlaskForm):
    """Form for setting break times."""
    time_format_validator = Regexp(r'^\d{2}:\d{2}$', message='Format must be HH:MM')
    
    lunch_start_time = StringField('Lunch Start Time', validators=[DataRequired(), time_format_validator])
    lunch_end_time = StringField('Lunch End Time', validators=[DataRequired(), time_format_validator])
    recess_start_time = StringField('Recess Start Time', validators=[DataRequired(), time_format_validator])
    recess_end_time = StringField('Recess End Time', validators=[DataRequired(), time_format_validator])
    submit = SubmitField('Update Break Times')