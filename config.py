import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-hard-to-guess-secret-key')

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost:5432/tenderdb')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')


    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-hard-to-guess-jwt-secret')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    JWT_ISSUER = os.environ.get('JWT_ISSUER', None)
    JWT_AUDIENCE = os.environ.get('JWT_AUDIENCE', None)
