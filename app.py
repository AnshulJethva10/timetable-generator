import random
from flask import Flask, render_template, redirect, url_for, flash

# Initialize the Flask App
app = Flask(__name__)
# A secret key is needed for flashing messages
app.config['SECRET_KEY'] = 'a-very-secret-key' 

# --- FAKE DATABASE (In-memory data for simplicity) ---
# In a real project, this data would come from a database like MySQL or PostgreSQL.

COURSES = {
    "CS101": {"name": "Intro to Python", "instructor": "Dr. Smith"},
    "MA202": {"name": "Calculus II", "instructor": "Dr. Jones"},
    "EN105": {"name": "Creative Writing", "instructor": "Prof. Williams"},
    "PH210": {"name": "Modern Physics", "instructor": "Dr. Davis"},
    "HI101": {"name": "World History", "instructor": "Prof. Miller"},
}

ROOMS = ["Room 101", "Room 102", "Auditorium A"]
TIMESLOTS = ["09:00 - 10:30", "11:00 - 12:30", "14:00 - 15:30"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# This will store our generated timetable
current_timetable = {}

# --- HELPER FUNCTION ---
def get_past_timetable_constraints():
    """
    Simulates analyzing past timetables to get constraints.
    """
    return {
        "CS101": {"preferred_room": "Auditorium A"},
        "MA202": {"avoid_day": "Friday"},
    }

# --- ROUTES ---

@app.route('/')
def index():
    """
    The main page that displays the current timetable.
    """
    # If the timetable is empty on the first visit, generate it.
    if not current_timetable:
        generate_timetable(flash_messages=False) # Generate without flashing
    return render_template('index.html', timetable=current_timetable, days=DAYS, timeslots=TIMESLOTS)

@app.route('/generate')
def handle_generate_request():
    """
    This is the route that gets called when the user clicks the button.
    It's responsible for calling the generation logic and redirecting.
    """
    generate_timetable(flash_messages=True) # Generate WITH flashing
    return redirect(url_for('index'))


# --- CORE LOGIC ---

# MODIFICATION 1: Add a parameter to control flashing
def generate_timetable(flash_messages=True):
    """
    This is the core logic for generating the timetable.
    It clears the old timetable and creates a new one.
    The flash_messages flag controls whether to show messages to the user.
    """
    global current_timetable
    current_timetable.clear()

    constraints = get_past_timetable_constraints()

    available_slots = []
    for day in DAYS:
        for time in TIMESLOTS:
            for room in ROOMS:
                available_slots.append({"day": day, "time": time, "room": room})
    
    random.shuffle(available_slots)

    generated_successfully = True
    for course_id, course_info in COURSES.items():
        slot_found = False
        for i, slot in enumerate(available_slots):
            if course_id in constraints:
                constraint = constraints[course_id]
                if constraint.get("preferred_room") and slot["room"] != constraint["preferred_room"]:
                    continue
                if constraint.get("avoid_day") and slot["day"] == constraint["avoid_day"]:
                    continue

            current_timetable[(slot["day"], slot["time"], slot["room"])] = {
                "course_id": course_id, 
                "name": course_info["name"],
                "instructor": course_info["instructor"]
            }
            available_slots.pop(i)
            slot_found = True
            break
        
        if not slot_found:
            if flash_messages: # Only flash if the flag is True
                flash(f"Could not find a suitable slot for {course_info['name']}! Try generating again.", "error")
            generated_successfully = False
            break

    if generated_successfully and flash_messages: # Only flash if the flag is True
        flash("Successfully generated a new timetable!", "success")


# To run the app
if __name__ == '__main__':
    # MODIFICATION 2: Remove the initial call from here. It's now handled by the index route.
    app.run(debug=True)