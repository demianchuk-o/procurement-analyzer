from celery import Celery
from celery.schedules import crontab

app = Celery('tender_tasks')
app.config_from_object('celeryconfig')

app.conf.beat_schedule = {
    'crawl-tenders-every-15-minutes': {
        'task': 'tasks.crawl_tenders_task',
        'schedule': crontab(minute='*/15'),
    },
    'sync-all-tenders-every-hour': {
        'task': 'tasks.sync_all_tenders_task',
        'schedule': crontab(minute=0, hour='*/1'),
    },
    'send-notifications-every-hour': {
        'task': 'tasks.send_notifications_task',
        'schedule': crontab(minute=0, hour='*/1'),
    },
}

if __name__ == '__main__':
    app.start()