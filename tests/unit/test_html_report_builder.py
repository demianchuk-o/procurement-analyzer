import pytest
from datetime import datetime

from services.html_report_builder import HtmlReportBuilder
from util.field_maps import get_field_map

value_amount_localized = get_field_map('tenders')['value_amount']
title_localized = get_field_map('tenders')['title']


class MockChange:
    def __init__(self, field_name, old_value, new_value, change_date):
        self.field_name = field_name
        self.old_value = old_value
        self.new_value = new_value
        self.change_date = change_date


FIXED_TEST_DATETIME = datetime(2024, 1, 15, 10, 30, 0)

class TestHtmlReportBuilder:

    @pytest.fixture
    def report_builder(self):
        """Fixture to create an instance of HtmlReportBuilder."""
        return HtmlReportBuilder()

    def test_generate_report_with_tender_changes(self, report_builder):
        """Test generating a report with tender changes."""
        # Arrange
        report_data = {
            "tender_info": "Tender ID: tender-123, Title: Test Tender",
            "tender_changes": [
                MockChange(field_name="title", old_value="Old Title", new_value="New Title", change_date=FIXED_TEST_DATETIME),
                MockChange(field_name="value_amount", old_value="1000", new_value="2000", change_date=FIXED_TEST_DATETIME)
            ],
            "new_entities": {
                "bids": [],
                "awards": [],
                "documents": [],
                "complaints": []
            },
            "entity_changes": {
                "bids": {},
                "awards": {},
                "documents": {},
                "complaints": {}
            }
        }

        # Act
        html_report = report_builder.generate_report(report_data)

        # Assert
        assert "<h1>Інформація про тендер:</h1>" in html_report 
        assert "<p>Tender ID: tender-123, Title: Test Tender</p>" in html_report
        assert "<h2>Зміни в тендері:</h2>" in html_report
        assert "<li>" in html_report # This confirms a list item is present
        assert title_localized in html_report
        assert value_amount_localized in html_report
        assert "<p>Не зафіксовано нових об'єктів.</p>" in html_report
        assert "<p>Немає відслідкованих змін.</p>" in html_report

    def test_generate_report_with_new_entities(self, report_builder):
        """Test generating a report with new entities."""
        # Arrange
        report_data = {
            "tender_info": "Tender ID: tender-456, Title: Another Tender",
            "tender_changes": [],
            "new_entities": {
                "bids": ["Bid ID: bid-1, Value: 500", "Bid ID: bid-2, Value: 750"],
                "awards": ["Award ID: award-1, Value: 1000"],
                "documents": [],
                "complaints": []
            },
            "entity_changes": {
                "bids": {},
                "awards": {},
                "documents": {},
                "complaints": {}
            }
        }

        # Act
        html_report = report_builder.generate_report(report_data)

        # Assert
        assert "<h1>Інформація про тендер:</h1>" in html_report
        assert "Another Tender</p>" in html_report
        assert "<h2>Зміни в тендері:</h2>" in html_report
        assert "<p>Не зафіксовано змін у тендері.</p>" in html_report
        assert "<h3>Новий об'єкт: Bids</h3>" in html_report
        assert "<li>Bid ID: bid-1, Value: 500</li>" in html_report
        assert "<h3>Новий об'єкт: Awards</h3>" in html_report
        assert "<li>Award ID: award-1, Value: 1000</li>" in html_report
        assert "<p>Немає відслідкованих змін.</p>" in html_report

    def test_generate_report_with_entity_changes(self, report_builder):
        """Test generating a report with entity changes."""
        # Arrange
        report_data = {
            "tender_info": "Tender ID: tender-789, Title: Final Tender",
            "tender_changes": [],
            "new_entities": {
                "bids": [],
                "awards": [],
                "documents": [],
                "complaints": []
            },
            "entity_changes": {
                "bids": {
                    "bid-1": {"info": "Bid ID: bid-1, Bidder: Bidder One", "changes": [
                        MockChange(field_name="value_amount", old_value="500", new_value="600", change_date=FIXED_TEST_DATETIME)
                    ]},
                    "bid-2": {"info": "Bid ID: bid-2, Bidder: Bidder Two", "changes": []}
                },
                "awards": {},
                "documents": {},
                "complaints": {}
            }
        }

        # Act
        html_report = report_builder.generate_report(report_data)

        # Assert
        assert "<h1>Інформація про тендер:</h1>" in html_report
        assert "Final Tender</p>" in html_report
        assert "<p>Не зафіксовано змін у тендері.</p>" in html_report
        assert "<p>Не зафіксовано нових об'єктів.</p>" in html_report
        assert "<h3>Bids Зміни</h3>" in html_report
        assert "<div class='entity-block'>" in html_report
        assert "<h4>Об'єкт: Bid ID: bid-1, Bidder: Bidder One</h4>" in html_report
        assert "<li class='change-item'>" in html_report
        assert value_amount_localized in html_report
        assert "<h4>Об'єкт: Bid ID: bid-2, Bidder: Bidder Two</h4>" in html_report
        assert "<p>Не відслідковано змін для даного об'єкту.</p>" in html_report

    def test_generate_report_empty(self, report_builder):
        """Test generating a report with no data."""
        # Arrange
        report_data = {
            "tender_info": "",
            "tender_changes": [],
            "new_entities": {
                "bids": [],
                "awards": [],
                "documents": [],
                "complaints": []
            },
            "entity_changes": {
                "bids": {},
                "awards": {},
                "documents": {},
                "complaints": {}
            }
        }

        # Act
        html_report = report_builder.generate_report(report_data)

        # Assert
        assert "<h1>Інформація про тендер:</h1>" in html_report
        assert "<p></p>" in html_report # empty tender info
        assert "<p>Не зафіксовано змін у тендері.</p>" in html_report
        assert "<p>Не зафіксовано нових об'єктів.</p>" in html_report
        assert "<p>Немає відслідкованих змін.</p>" in html_report