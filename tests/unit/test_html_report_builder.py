import pytest

from services.html_report_builder import HtmlReportBuilder
from util.field_maps import get_field_map

value_amount_localized = get_field_map('tenders')['value_amount']
title_localized = get_field_map('tenders')['title']

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
                {"field_name": "title", "old_value": "Old Title", "new_value": "New Title"},
                {"field_name": "value_amount", "old_value": "1000", "new_value": "2000"}
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
        assert "<h1>Tender Information</h1>" in html_report
        assert "<p>Tender ID: tender-123, Title: Test Tender</p>" in html_report
        assert "<h2>Tender Changes</h2>" in html_report
        assert "<li>" in html_report
        assert title_localized in html_report


        assert value_amount_localized in html_report
        assert "<p>No new entities.</p>" in html_report
        assert "<p>No entity changes.</p>" in html_report

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
        assert "<h1>Tender Information</h1>" in html_report
        assert "Another Tender</p>" in html_report
        assert "<h2>Tender Changes</h2>" in html_report
        assert "<p>No tender changes.</p>" in html_report
        assert "<h3>New Bids</h3>" in html_report
        assert "<li>Bid ID: bid-1, Value: 500</li>" in html_report
        assert "<h3>New Awards</h3>" in html_report
        assert "<li>Award ID: award-1, Value: 1000</li>" in html_report
        assert "<p>No entity changes.</p>" in html_report

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
                    "bid-1": {"info": "Bid ID: bid-1, Bidder: Bidder One", "changes": [{"field_name": "value_amount", "old_value": "500", "new_value": "600"}]},
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
        assert "<h1>Tender Information</h1>" in html_report
        assert "Final Tender</p>" in html_report
        assert "<p>No tender changes.</p>" in html_report
        assert "<p>No new entities.</p>" in html_report
        assert "<h3>Bids Changes</h3>" in html_report
        assert "<div class='entity-block'>" in html_report
        assert "<h4>Entity: Bid ID: bid-1, Bidder: Bidder One</h4>" in html_report
        assert "<li class='change-item'>" in html_report
        assert value_amount_localized in html_report
        assert "<h4>Entity: Bid ID: bid-2, Bidder: Bidder Two</h4>" in html_report
        assert "<p>No changes recorded for this entity.</p>" in html_report

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
        assert "<h1>Tender Information</h1>" in html_report
        assert "<p></p>" in html_report
        assert "<p>No tender changes.</p>" in html_report
        assert "<p>No new entities.</p>" in html_report
        assert "<p>No entity changes.</p>" in html_report