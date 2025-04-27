import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-hard-to-guess-secret-key')

    MIGRATION_LOCAL = os.getenv('MIGRATION_LOCAL', 'false').lower() in ('1', 'true', 'yes')

    DB_HOST = 'localhost' if MIGRATION_LOCAL else os.getenv('DB_HOST', 'db')
    DB_PORT = os.getenv('DB_PORT_LOCAL', '5434') if MIGRATION_LOCAL else os.getenv('DB_PORT', '5432')

    # always build this
    _DEFAULT_URI = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{DB_HOST}:{DB_PORT}/{os.getenv('DB_NAME')}"
    )

    # ignore DATABASE_URL when migrating locally
    SQLALCHEMY_DATABASE_URI = (
        _DEFAULT_URI if MIGRATION_LOCAL
        else os.getenv('DATABASE_URL', _DEFAULT_URI)
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')


    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-hard-to-guess-jwt-secret')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))

    JWT_ENCODE_ISSUER = os.environ.get('JWT_ISSUER', None)
    JWT_ENCODE_AUDIENCE = os.environ.get('JWT_AUDIENCE', None)

    JWT_DECODE_ISSUER = os.environ.get('JWT_ISSUER', None)
    JWT_DECODE_AUDIENCE = os.environ.get('JWT_AUDIENCE', None)
