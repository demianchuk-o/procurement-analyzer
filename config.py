import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-hard-to-guess-secret-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost:5434/tenderdb')
    SQLALCHEMY_TEST_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'postgresql://user:pass@localhost:5434/test_tenderdb')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')