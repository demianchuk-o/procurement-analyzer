import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, smtp_server: str, port: int, sender_email: str, password: str, use_tls: bool = True):
        self.smtp_server = smtp_server
        self.port = port
        self.sender_email = sender_email
        self.password = password
        self.use_tls = use_tls
        self.context = ssl.create_default_context()

    def send_report(self, recipient_email: str, subject: str, html_body: str) -> bool:
        """Sends an HTML email report."""
        message = MIMEMultipart("alternative")
        message["From"] = self.sender_email
        message["To"] = recipient_email
        message["Subject"] = subject

        part = MIMEText(html_body, "html")

        message.attach(part)

        try:
            with smtplib.SMTP(self.smtp_server, self.port) as server:
                if self.use_tls:
                    server.starttls(context=self.context)
                server.login(self.sender_email, self.password)
                server.sendmail(self.sender_email, recipient_email, message.as_string())
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
        except Exception as e:
            logger.exception(f"Failed to send email to {recipient_email}: {e}")
            return False