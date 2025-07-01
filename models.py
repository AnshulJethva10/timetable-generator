from flask_login import UserMixin
from werkzeug.security import check_password_hash
from bson import ObjectId

# Import from the new extensions.py file
from extensions import mongo

class User(UserMixin):
    """
    User model for interacting with the 'users' collection in MongoDB.
    """
    def __init__(self, user_data):
        self.id = str(user_data.get('_id'))
        self.username = user_data.get('username')
        self.password = user_data.get('password')
        self.role = user_data.get('role')

    def check_password(self, password_to_check):
        """Checks if the provided password matches the stored hash."""
        return check_password_hash(self.password, password_to_check)

    @staticmethod
    def find_by_username(username):
        """Finds a user by their username."""
        # The mongo object is now safely imported from extensions.py at the top level
        user_data = mongo.db.users.find_one({'username': username})
        if user_data:
            return User(user_data)
        return None
