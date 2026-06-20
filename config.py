import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'database', 'picoprog.db')

    SECRET_KEY = os.getenv('SECRET_KEY')

    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
