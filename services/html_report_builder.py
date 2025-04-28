import logging
from typing import Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

from util.report_helpers import format_entity_change

logger = logging.getLogger(__name__)

class HtmlReportBuilder:
    def __init__(self, template_dir='templates', template_name='report_template.html'):
        templates_path = os.path.join(os.path.dirname(__file__), '..', template_dir)
        self.env = Environment(
            loader=FileSystemLoader(templates_path),
            autoescape=select_autoescape(['html', 'xml'])
        )
        self.template = self.env.get_template(template_name)
        self.env.globals['format_entity_change'] = format_entity_change


    def generate_report(self, report_data: Dict) -> str:
        """Generates an HTML report from the structured data using a Jinja2 template."""
        logger.info("Generating HTML report using Jinja2 template...")

        html_report = self.template.render(report_data)

        logger.info("HTML report generated.")
        return html_report
