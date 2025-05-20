import logging

from celery_app import app as celery_app
from repositories.tender_repository import TenderRepository
from services.crawler_service import CrawlerService
from services.datetime_provider import DatetimeProvider
from services.email_service import EmailService
from services.html_report_builder import HtmlReportBuilder
from services.notification_service import NotificationService
from app import app
from services.report_generation_service import ReportGenerationService
from util.db_context_manager import session_scope


@celery_app.task(name='tasks.crawl_tenders_task')
def crawl_tenders_task():
    with app.app_context(), session_scope() as session:
        tender_repository = TenderRepository(session)
        crawler_service = CrawlerService(tender_repository)
        crawler_service.crawl_tenders(pages_to_crawl=1)
        session.commit()

@celery_app.task(name='tasks.sync_all_tenders_task')
def sync_all_tenders_task():
    with app.app_context(), session_scope() as session:
        tender_repository = TenderRepository(session)
        crawler_service = CrawlerService(tender_repository)
        crawler_service.sync_all_tenders()
        session.commit()

@celery_app.task(
    name='tasks.send_batch_email_task',
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def send_batch_email_task(self, recipients: list, subject: str, html_body: str):
    """
    Send one email per recipient over a single SMTP connection.
    """
    try:
        logger = logging.getLogger(__name__)
        with app.app_context():
            with EmailService(
                smtp_server=app.config['SMTP_SERVER'],
                port=app.config['SMTP_PORT'],
                sender_email=app.config['SMTP_USER'],
                password=app.config['SMTP_PASSWORD']
            ) as email_service:
                for rcpt in recipients:
                    try:
                        email_service.send(rcpt, subject, html_body)
                    except Exception as e:
                        rcpt_masked = rcpt[:2] + "****" + rcpt[-2:]
                        logger.error(f"Failed to send email to {rcpt_masked} {e}", exc_info=True)
    except Exception as exc:
        logger.exception("Batch email task failed, retrying...")
        raise self.retry(exc=exc)

@celery_app.task(name='tasks.send_notifications_task')
def send_notifications_task():
    with app.app_context(), session_scope() as session:
        notification_service = NotificationService(
            tender_repository=TenderRepository(session),
            report_generator=ReportGenerationService(session),
            html_builder=HtmlReportBuilder(),
            datetime_provider=DatetimeProvider(),
            report_interval_min=15
        )
        notification_service.send_notifications()