from celery import Celery


app = Celery('tender_complaints')  # Replace 'tender_complaints' with your project name
app.config_from_object('celeryconfig')

if __name__ == '__main__':
    app.start()