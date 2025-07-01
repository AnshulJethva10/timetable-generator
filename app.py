import os
from flask import Flask
from werkzeug.security import generate_password_hash
from bson import ObjectId
from pymongo.errors import ConnectionFailure

# Import extensions from the new extensions.py file
from extensions import mongo, login_manager

# The user_loader callback is defined here, using the imported login_manager
@login_manager.user_loader
def load_user(user_id):
    from models import User
    user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    if not user_data:
        return None
    return User(user_data)


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_super_secret_key_change_it'
    
    # Your MongoDB Atlas connection string
    app.config['MONGO_URI'] = ""
    
    # Initialize the extensions with the app instance
    try:
        mongo.init_app(app)
        login_manager.init_app(app)
        
        # Verify connection
        mongo.cx.admin.command('ismaster') 
        print("MongoDB connection successful.")
    except ConnectionFailure as e:
        raise ConnectionFailure(f"FATAL: Could not connect to MongoDB. Check your MONGO_URI and network access. Original error: {e}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred during MongoDB initialization: {e}")

    # Configure login manager
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    # Import and register blueprints
    from routes import main_bp
    app.register_blueprint(main_bp)

    @app.before_request
    def ensure_admin_user():
        if not hasattr(app, '_admin_user_created'):
            users_collection = mongo.db.users
            if not users_collection.find_one({'username': 'admin'}):
                hashed_password = generate_password_hash('adminpassword', method='pbkdf2:sha256')
                users_collection.insert_one({
                    'username': 'admin',
                    'password': hashed_password,
                    'role': 'admin'
                })
                print("Default admin user created.")
            app._admin_user_created = True

    return app

if __name__ == '__main__':
    try:
        app = create_app()
        app.run(debug=True)
    except (ValueError, ConnectionFailure) as e:
        print(e)
