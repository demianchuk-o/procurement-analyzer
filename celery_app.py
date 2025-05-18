import logging

from celery import Celery
from celery.schedules import crontab

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

import signals

app = Celery(
    'tender_tasks',
    include=[
        'services.data_processor',
        'services.complaint_analysis_service',
        'tasks',
    ]
)
app.config_from_object('celeryconfig')

app.conf.beat_schedule = {
    'crawl-tenders': {
        'task': 'tasks.crawl_tenders_task',
        'schedule': crontab(minute='*/15'),
    },
    'sync-all-tenders': {
        'task': 'tasks.sync_all_tenders_task',
        'schedule': crontab(minute='*/30'),
    },
    'send-notifications': {
        'task': 'tasks.send_notifications_task',
        'schedule': crontab(minute='*/30'),
    },
}

if __name__ == '__main__':
    app.start()