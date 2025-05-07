import logging
from datetime import timedelta

from repositories.tender_repository import TenderRepository
from services.datetime_provider import DatetimeProvider
from services.email_service import EmailService
from services.html_report_builder import HtmlReportBuilder
from services.report_generation_service import ReportGenerationService

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, tender_repository: TenderRepository, report_generator: ReportGenerationService,
                    html_builder: HtmlReportBuilder, email_service: EmailService,
                    datetime_provider: DatetimeProvider, report_interval_hours: int = 1):
        self.tender_repo = tender_repository
        self.report_generator = report_generator
        self.html_builder = html_builder
        self.email_service = email_service
        self.datetime_provider = datetime_provider
        self.report_interval = timedelta(hours=report_interval_hours)

    def send_notifications(self):
        """
        Fetches recently modified tenders, generates reports, and sends
        notifications to subscribed users.
        """
        since_date = self.datetime_provider.utc_now() - self.report_interval
        logger.info(f"Starting notification process for tenders modified since {since_date}")

        try:
            # Get modified tenders and subscribed users
            tender_user_map = self.tender_repo.get_modified_tenders_and_subscribed_users(since_date)
            logger.info(f"Found {len(tender_user_map)} tenders with modifications and subscriptions.")

            if not tender_user_map:
                logger.info("No tenders require notifications.")
                return

            for tender_id, user_emails in tender_user_map.items():
                logger.info(f"Processing tender ID: {tender_id} for {len(user_emails)} users.")
                try:
                    report_data = self.report_generator.generate_tender_report(tender_id=tender_id,
                                                                               new_since=since_date,
                                                                               changes_since=since_date)

                    html_report = self.html_builder.generate_report(report_data)
                    tender_title = report_data.get("tender_info", f"Tender {tender_id}")
                    subject = f"Оновлення тендеру: {tender_title}"


                    for email in user_emails:
                        self.email_service.send_report(email, subject, html_report)
                        email_split = email.split('@')
                        email_formatted = f"{email_split[0][:2]}***@{email_split[1]}"
                        logger.debug(f"Sent notification for tender {tender_id} to {email_formatted}")

                except ValueError as e:
                     logger.error(f"Could not generate report for tender {tender_id}: {e}")
                except Exception as e:
                    logger.exception(f"Unexpected error processing tender {tender_id}: {e}")

        except Exception as e:
            logger.exception(f"Failed during notification process: {e}")

        logger.info("Notification process finished.")