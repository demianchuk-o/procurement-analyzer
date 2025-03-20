import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-hard-to-guess-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost:5434/tenderdb')
    SQLALCHEMY_TRACK_MODIFICATIONS = False