import pytest
from unittest.mock import MagicMock, call
from datetime import datetime, timedelta, timezone

from repositories.tender_repository import TenderRepository
from services.email_service import EmailService
from services.html_report_builder import HtmlReportBuilder
from services.notification_service import NotificationService
from services.report_generation_service import ReportGenerationService
from services.datetime_provider import DatetimeProvider


class TestNotificationService:

    @pytest.fixture
    def mock_tender_repo(self):
        return MagicMock(spec=TenderRepository)

    @pytest.fixture
    def mock_report_generator(self):
        return MagicMock(spec=ReportGenerationService)

    @pytest.fixture
    def mock_html_builder(self):
        return MagicMock(spec=HtmlReportBuilder)

    @pytest.fixture
    def mock_email_service(self):
        return MagicMock(spec=EmailService)

    @pytest.fixture
    def mock_datetime_provider(self):
        return MagicMock(spec=DatetimeProvider)

    @pytest.fixture
    def notification_service(self, mock_tender_repo, mock_report_generator,
                             mock_html_builder, mock_email_service, mock_datetime_provider):
        return NotificationService(
            tender_repository=mock_tender_repo,
            report_generator=mock_report_generator,
            html_builder=mock_html_builder,
            email_service=mock_email_service,
            datetime_provider=mock_datetime_provider,
            report_interval_hours=1
        )

    @pytest.fixture
    def test_now(self):
        return datetime(2023, 10, 27, 12, 0, 0, tzinfo=timezone.utc)

    @pytest.fixture
    def since_date(self, test_now):
        return test_now - timedelta(hours=1)

    def test_send_notifications_no_tenders(self, notification_service, mock_tender_repo, mock_report_generator, mock_html_builder, mock_email_service, mock_datetime_provider, since_date, test_now):
        """Test send_notifications when no modified tenders are found."""
        mock_tender_repo.get_modified_tenders_and_subscribed_users.return_value = {}
        mock_datetime_provider.utc_now.return_value = test_now

        notification_service.send_notifications()

        mock_tender_repo.get_modified_tenders_and_subscribed_users.assert_called_once_with(since_date)
        mock_report_generator.generate_tender_report.assert_not_called()
        mock_html_builder.generate_report.assert_not_called()
        mock_email_service.send_report.assert_not_called()
        mock_datetime_provider.utc_now.assert_called_once()

    def test_send_notifications_success(self, notification_service, mock_tender_repo, mock_report_generator, mock_html_builder, mock_email_service, mock_datetime_provider, since_date, test_now):
        """Test the successful flow of sending notifications."""
        tender_id_1 = "tender-1"
        tender_id_2 = "tender-2"
        emails_1 = ["user1@example.com", "user2@example.com"]
        emails_2 = ["user3@example.com"]
        report_data_1 = {"tender_info": "Tender 1 Info", "tender_changes": [{"f": "v"}]}
        report_data_2 = {"tender_info": "Tender 2 Info", "new_entities": {"bids": ["b1"]}}
        html_report_1 = "<html>Report 1</html>"
        html_report_2 = "<html>Report 2</html>"
        subject_1 = "Оновлення тендеру: Tender 1 Info"
        subject_2 = "Оновлення тендеру: Tender 2 Info"

        mock_tender_repo.get_modified_tenders_and_subscribed_users.return_value = {
            tender_id_1: emails_1,
            tender_id_2: emails_2,
        }
        mock_report_generator.generate_tender_report.side_effect = [report_data_1, report_data_2]
        mock_html_builder.generate_report.side_effect = [html_report_1, html_report_2]
        mock_datetime_provider.utc_now.return_value = test_now

        notification_service.send_notifications()

        # Verify calls
        mock_tender_repo.get_modified_tenders_and_subscribed_users.assert_called_once_with(since_date)
        mock_report_generator.generate_tender_report.assert_has_calls([
            call(tender_id_1, since_date),
            call(tender_id_2, since_date),
        ])
        mock_html_builder.generate_report.assert_has_calls([
            call(report_data_1),
            call(report_data_2),
        ])
        mock_email_service.send_report.assert_has_calls([
            call(emails_1[0], subject_1, html_report_1),
            call(emails_1[1], subject_1, html_report_1),
            call(emails_2[0], subject_2, html_report_2),
        ], any_order=True)
        mock_datetime_provider.utc_now.assert_called_once()

    def test_send_notifications_report_generation_error(self, notification_service, mock_tender_repo, mock_report_generator, mock_html_builder, mock_email_service, mock_datetime_provider, since_date, test_now):
        """Test handling of ValueError during report generation."""
        tender_id_1 = "tender-fail"
        emails_1 = ["user1@example.com"]

        mock_tender_repo.get_modified_tenders_and_subscribed_users.return_value = {
            tender_id_1: emails_1,
        }
        mock_report_generator.generate_tender_report.side_effect = ValueError("Report failed")
        mock_datetime_provider.utc_now.return_value = test_now

        notification_service.send_notifications()

        mock_tender_repo.get_modified_tenders_and_subscribed_users.assert_called_once_with(since_date)
        mock_report_generator.generate_tender_report.assert_called_once_with(tender_id_1, since_date)
        mock_html_builder.generate_report.assert_not_called()
        mock_email_service.send_report.assert_not_called()
        mock_datetime_provider.utc_now.assert_called_once()

    def test_send_notifications_unexpected_error(self, notification_service, mock_tender_repo, mock_report_generator, mock_html_builder, mock_email_service, mock_datetime_provider, since_date, test_now):
        """Test handling of unexpected errors during processing."""
        tender_id_1 = "tender-ok"
        tender_id_2 = "tender-fail"
        emails_1 = ["user1@example.com"]
        emails_2 = ["user2@example.com"]
        report_data_1 = {"tender_info": "Tender 1 Info", "tender_changes": [{"f": "v"}]}
        html_report_1 = "<html>Report 1</html>"
        subject_1 = "Оновлення тендеру: Tender 1 Info"

        mock_tender_repo.get_modified_tenders_and_subscribed_users.return_value = {
            tender_id_1: emails_1,
            tender_id_2: emails_2,
        }
        # Fail on the second tender's report generation
        mock_report_generator.generate_tender_report.side_effect = [
            report_data_1,
            Exception("Something broke")
        ]
        mock_html_builder.generate_report.return_value = html_report_1
        mock_datetime_provider.utc_now.return_value = test_now

        notification_service.send_notifications()

        mock_report_generator.generate_tender_report.assert_has_calls([
            call(tender_id_1, since_date),
            call(tender_id_2, since_date),  # was called before the exception
        ])
        mock_html_builder.generate_report.assert_called_once_with(report_data_1)
        mock_email_service.send_report.assert_called_once_with(emails_1[0], subject_1, html_report_1)
        mock_datetime_provider.utc_now.assert_called_once()