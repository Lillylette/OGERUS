import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'ogers.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join('static')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024