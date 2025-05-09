from config import Config

broker_url = Config.CELERY_BROKER_URL
result_backend = Config.CELERY_RESULT_BACKEND
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

worker_prefetch_multiplier = 1
task_acks_late = True