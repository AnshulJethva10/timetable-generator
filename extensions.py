from flask_pymongo import PyMongo
from flask_login import LoginManager

# Initialize extensions here, without attaching them to an app
mongo = PyMongo()
login_manager = LoginManager()
