import pytest
from unittest.mock import MagicMock, call, patch
from datetime import datetime, timedelta, timezone

from repositories.tender_repository import TenderRepository
from services.html_report_builder import HtmlReportBuilder
from services.notification_service import NotificationService
from services.report_generation_service import ReportGenerationService
from services.datetime_provider import DatetimeProvider


@patch('tasks.send_batch_email_task')
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
    def mock_datetime_provider(self):
        return MagicMock(spec=DatetimeProvider)

    @pytest.fixture
    def notification_service(self, mock_tender_repo, mock_report_generator,
                             mock_html_builder, mock_datetime_provider): # mock_email_service removed
        return NotificationService(
            tender_repository=mock_tender_repo,
            report_generator=mock_report_generator,
            html_builder=mock_html_builder,
            datetime_provider=mock_datetime_provider,
            report_interval_min=30
        )

    @pytest.fixture
    def test_now(self):
        return datetime(2023, 10, 27, 12, 0, 0, tzinfo=timezone.utc)

    @pytest.fixture
    def since_date(self, test_now, notification_service):
        return test_now - notification_service.report_interval

    def test_send_notifications_no_tenders(self, mock_send_task, notification_service, mock_tender_repo, mock_datetime_provider, since_date, test_now): # mock_send_task added, mock_email_service removed
        """Test send_notifications when no modified tenders are found."""
        # Arrange
        mock_datetime_provider.utc_now.return_value = test_now
        mock_tender_repo.get_modified_tenders_and_subscribed_users.return_value = {}

        # Act
        notification_service.send_notifications()

        # Assert
        mock_datetime_provider.utc_now.assert_called_once()
        mock_tender_repo.get_modified_tenders_and_subscribed_users.assert_called_once_with(since_date)
        mock_send_task.apply_async.assert_not_called() # Check that the task was not called

    def test_send_notifications_success(self, mock_send_task, notification_service, mock_tender_repo, mock_report_generator, mock_html_builder, mock_datetime_provider, since_date, test_now):
        """Test successful notification sending for multiple tenders and users."""
        # Arrange
        mock_datetime_provider.utc_now.return_value = test_now
        tender_user_map = {
            "tender_id_1": ["user1@example.com", "user2@example.com"],
            "tender_id_2": ["user3@example.com"]
        }
        report_data_1 = {"tender_info": "Tender 1 Info", "tender_changes": [{"field": "value1"}]}
        report_data_2 = {"tender_info": "Tender 2 Info", "tender_changes": [{"field": "value2"}]}
        html_report_1 = "<html>Report 1</html>"
        html_report_2 = "<html>Report 2</html>"
        subject_1 = "Оновлення тендеру: Tender 1 Info"
        subject_2 = "Оновлення тендеру: Tender 2 Info"

        mock_tender_repo.get_modified_tenders_and_subscribed_users.return_value = tender_user_map
        mock_report_generator.generate_tender_report.side_effect = [report_data_1, report_data_2]
        mock_html_builder.generate_report.side_effect = [html_report_1, html_report_2]

        # Act
        notification_service.send_notifications()

        # Assert
        mock_datetime_provider.utc_now.assert_called_once()
        mock_tender_repo.get_modified_tenders_and_subscribed_users.assert_called_once_with(since_date)

        mock_report_generator.generate_tender_report.assert_has_calls([
            call(tender_id="tender_id_1", new_since=since_date, changes_since=since_date, fetch_new_entities=True, fetch_entity_changes=True),
            call(tender_id="tender_id_2", new_since=since_date, changes_since=since_date, fetch_new_entities=True, fetch_entity_changes=True)
        ])
        mock_html_builder.generate_report.assert_has_calls([
            call(report_data_1),
            call(report_data_2)
        ])

        expected_task_calls = [
            call(args=(["user1@example.com", "user2@example.com"], subject_1, html_report_1), queue='email_queue'),
            call(args=(["user3@example.com"], subject_2, html_report_2), queue='email_queue')
        ]
        mock_send_task.apply_async.assert_has_calls(expected_task_calls)

    def test_send_notifications_report_generation_failure(self, mock_send_task, notification_service, mock_tender_repo,
                                                          mock_html_builder, mock_report_generator,
                                                          mock_datetime_provider, since_date, test_now):
        """Test that one failed report generation doesn't stop others."""
        # Arrange
        mock_datetime_provider.utc_now.return_value = test_now
        tender_user_map = {
            "tender_id_1": ["user1@example.com"],
            "tender_id_fail": ["user_fail@example.com"],
            "tender_id_2": ["user2@example.com"]
        }
        report_data_1 = {"tender_info": "Tender 1 Info"}
        report_data_2 = {"tender_info": "Tender 2 Info"}
        html_report_1 = "<html>Report 1</html>"
        html_report_2 = "<html>Report 2</html>"
        subject_1 = "Оновлення тендеру: Tender 1 Info"
        subject_2 = "Оновлення тендеру: Tender 2 Info"

        mock_tender_repo.get_modified_tenders_and_subscribed_users.return_value = tender_user_map
        mock_report_generator.generate_tender_report.side_effect = [
            report_data_1,
            ValueError("Failed to generate report for tender_id_fail"),
            report_data_2
        ]
        mock_html_builder.generate_report.side_effect = [html_report_1, html_report_2]

        # Act
        notification_service.send_notifications()

        # Assert
        mock_report_generator.generate_tender_report.assert_has_calls([
            call(tender_id="tender_id_1", new_since=since_date, changes_since=since_date, fetch_new_entities=True, fetch_entity_changes=True),
            call(tender_id="tender_id_fail", new_since=since_date, changes_since=since_date, fetch_new_entities=True, fetch_entity_changes=True),
            call(tender_id="tender_id_2", new_since=since_date, changes_since=since_date, fetch_new_entities=True, fetch_entity_changes=True)
        ])
        mock_html_builder.generate_report.assert_has_calls([
            call(report_data_1),
            call(report_data_2)
        ])

        expected_task_calls = [
            call(args=(["user1@example.com"], subject_1, html_report_1), queue='email_queue'),
            call(args=(["user2@example.com"], subject_2, html_report_2), queue='email_queue')
        ]
        assert mock_send_task.apply_async.call_count == 2
        mock_send_task.apply_async.assert_has_calls(expected_task_calls, any_order=False)


    def test_send_notifications_unexpected_error_in_loop(self, mock_send_task, notification_service, mock_tender_repo, mock_report_generator, mock_html_builder, mock_datetime_provider, since_date, test_now):
        """Test handling of unexpected error during processing a single tender in the loop."""
        mock_datetime_provider.utc_now.return_value = test_now
        emails_1 = ["user1@example.com"]
        emails_2 = ["user2@example.com"] # will cause an error after report generation
        emails_3 = ["user3@example.com"]

        report_data_1 = {"tender_info": "Tender 1 Info"}
        report_data_2 = {"tender_info": "Tender 2 Info (error after this)"} # report for the failing tender
        report_data_3 = {"tender_info": "Tender 3 Info"}

        html_report_1 = "<html>Report 1</html>"
        html_report_2 = "<html>Report 2 (error after this)</html>" # HTML for the failing tender
        html_report_3 = "<html>Report 3</html>"

        subject_1 = "Оновлення тендеру: Tender 1 Info"
        # subject_2 is for the failing tender
        subject_3 = "Оновлення тендеру: Tender 3 Info"


        mock_tender_repo.get_modified_tenders_and_subscribed_users.return_value = {
            "tender_id_1": emails_1,
            "tender_id_err": emails_2,
            "tender_id_3": emails_3
        }
        mock_report_generator.generate_tender_report.side_effect = [report_data_1, report_data_2, report_data_3]
        mock_html_builder.generate_report.side_effect = [html_report_1, html_report_2, html_report_3]

        mock_send_task.apply_async.side_effect = [
            None,
            Exception("SMTP server down"),
            None
        ]

        # Act
        notification_service.send_notifications()

        # Assert
        mock_report_generator.generate_tender_report.assert_has_calls([
            call(tender_id="tender_id_1", new_since=since_date, changes_since=since_date, fetch_new_entities=True, fetch_entity_changes=True),
            call(tender_id="tender_id_err", new_since=since_date, changes_since=since_date, fetch_new_entities=True, fetch_entity_changes=True),
            call(tender_id="tender_id_3", new_since=since_date, changes_since=since_date, fetch_new_entities=True, fetch_entity_changes=True)
        ])
        mock_html_builder.generate_report.assert_has_calls([
            call(report_data_1),
            call(report_data_2),
            call(report_data_3)
        ])

        # check that apply_async was attempted for all, but only succeeded for non-erroring ones
        expected_task_calls = [
            call(args=(emails_1, subject_1, html_report_1), queue='email_queue'),
            call(args=(emails_2, "Оновлення тендеру: Tender 2 Info (error after this)", html_report_2), queue='email_queue'),
            call(args=(emails_3, subject_3, html_report_3), queue='email_queue')
        ]
        assert mock_send_task.apply_async.call_count == 3
        mock_send_task.apply_async.assert_has_calls(expected_task_calls)
        mock_datetime_provider.utc_now.assert_called_once()

    def test_send_notifications_repo_failure(self, mock_send_task, notification_service, mock_tender_repo, mock_datetime_provider, test_now):
        """Test behavior when the tender repository fails."""
        # Arrange
        mock_datetime_provider.utc_now.return_value = test_now
        mock_tender_repo.get_modified_tenders_and_subscribed_users.side_effect = Exception("DB connection error")

        # Act
        notification_service.send_notifications()

        # Assert
        mock_datetime_provider.utc_now.assert_called_once()
        mock_tender_repo.get_modified_tenders_and_subscribed_users.assert_called_once()
        mock_send_task.apply_async.assert_not_called() # No emails should be sent