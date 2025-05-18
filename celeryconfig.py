from kombu import Queue, Exchange

from config import Config

broker_url = Config.CELERY_BROKER_URL
result_backend = Config.CELERY_RESULT_BACKEND
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

task_default_queue = 'default'
task_queues = (
    Queue('default',
          Exchange('default'),
          routing_key='default',
          queue_arguments={'x-max-priority': 10}),
    Queue('email_queue', Exchange('email_queue'), routing_key='email_queue'),
)

task_routes = {
    'tasks.send_batch_email_task': {
        'queue': 'email_queue',
        'routing_key': 'email_queue'
    },
}