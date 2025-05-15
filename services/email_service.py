import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self, smtp_server: str, port: int,
                 sender_email: str, password: str,
                 use_tls: bool = True):
        self.smtp_server = smtp_server
        self.port = port
        self.sender_email = sender_email
        self.password = password
        self.use_tls = use_tls
        self.context = ssl.create_default_context()

    def __enter__(self):
        self.server = smtplib.SMTP(self.smtp_server, self.port, timeout=10)
        if self.use_tls:
            self.server.starttls(context=self.context)
        if not self.sender_email or not self.password:
            raise RuntimeError("SMTP credentials are not set")
        self.server.login(self.sender_email, self.password)
        return self

    def send(self, recipient_email: str,
             subject: str, html_body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["From"] = self.sender_email
        msg["To"] = recipient_email
        msg["Subject"] = subject
        part = MIMEText(html_body, "html")
        msg.attach(part)

        self.server.sendmail(
            self.sender_email,
            recipient_email,
            msg.as_string()
        )
        logger.info(f"Email sent to {recipient_email}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.server.quit()
        except Exception as e:
            logger.warning(f"Error quitting SMTP server: {e}")