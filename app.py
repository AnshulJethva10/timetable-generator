import os
from flask import Flask
from werkzeug.security import generate_password_hash
from bson import ObjectId
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

# Load environment variables from a .env file for local development
load_dotenv()

# Import extensions from the new extensions.py file
from extensions import mongo, login_manager

# The user_loader callback is defined here, using the imported login_manager
@login_manager.user_loader
def load_user(user_id):
    """Load user from the database."""
    from models import User
    # Find user by ObjectId
    user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if not user_data:
        return None
    return User(user_data)


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)

    # --- Configuration Section ---
    # Load secret key and MongoDB URI from environment variables
    # This is more secure than hardcoding them in the file.
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['MONGO_URI'] = os.environ.get('MONGO_URI')

    # --- Validation Section ---
    # Raise an error if essential configuration is missing.
    # This helps catch configuration issues early.
    if not app.config['SECRET_KEY']:
        raise ValueError("FATAL: No SECRET_KEY environment variable set. Please set it in your .env file or hosting environment.")
    if not app.config['MONGO_URI']:
        raise ValueError("FATAL: No MONGO_URI environment variable set. Please set it in your .env file or hosting environment.")

    # --- Extensions Initialization ---
    # Initialize Flask extensions with the app instance.
    try:
        mongo.init_app(app)
        login_manager.init_app(app)
        
        # Verify the database connection to ensure the URI is correct and the server is reachable.
        mongo.cx.admin.command('ismaster') 
        print("MongoDB connection successful.")
    except ConnectionFailure as e:
        # Provide a more informative error message if the connection fails.
        raise ConnectionFailure(f"FATAL: Could not connect to MongoDB. Check your MONGO_URI and network access. Original error: {e}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred during MongoDB initialization: {e}")

    # --- Login Manager Configuration ---
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    # --- Blueprints Registration ---
    # Import and register the main blueprint for application routes.
    from routes import main_bp
    app.register_blueprint(main_bp)

    # --- Application Hooks ---
    @app.before_request
    def ensure_admin_user():
        """Create a default admin user if one doesn't exist."""
        # Use a flag on the app context to ensure this runs only once per app start.
        if not hasattr(app, '_admin_user_created'):
            with app.app_context():
                users_collection = mongo.db.users
                if not users_collection.find_one({'username': 'admin'}):
                    # Use a more secure password hashing method
                    hashed_password = generate_password_hash('adminpassword', method='pbkdf2:sha256')
                    users_collection.insert_one({
                        'username': 'admin',
                        'password': hashed_password,
                        'role': 'admin'
                    })
                    print("Default admin user created.")
                # Set the flag to prevent this check on subsequent requests
                app._admin_user_created = True

    return app

# --- Main Execution Block ---
if __name__ == '__main__':
    try:
        # Create the Flask app instance
        app = create_app()
        # Run the app in debug mode for development
        app.run(debug=True)
    except (ValueError, ConnectionFailure) as e:
        # Catch configuration and connection errors on startup and print them.
        print(e)