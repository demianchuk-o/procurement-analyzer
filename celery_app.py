from celery import Celery
from celery.schedules import crontab

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = Celery('tender_tasks')
app.config_from_object('celeryconfig')

import tasks

app.conf.beat_schedule = {
    'crawl-tenders-every-15-minutes': {
        'task': 'tasks.crawl_tenders_task',
        'schedule': crontab(minute='*/1'),
    },
    'sync-all-tenders-every-hour': {
        'task': 'tasks.sync_all_tenders_task',
        'schedule': crontab(minute='*/2'),
    },
    'send-notifications-every-hour': {
        'task': 'tasks.send_notifications_task',
        'schedule': crontab(minute='*/2'),
    },
}

if __name__ == '__main__':
    app.start()