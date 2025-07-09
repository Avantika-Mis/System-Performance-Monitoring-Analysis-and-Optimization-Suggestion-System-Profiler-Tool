# alerts/alert_manager.py

import logging
import smtplib
from email.message import EmailMessage

class AlertManager:
    def __init__(self, email_notifications_enabled=False, alert_email_recipients=None):
        self.email_notifications_enabled = email_notifications_enabled
        self.alert_email_recipients = alert_email_recipients or []
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def trigger_alert(self, message):
        self.logger.warning(f"ALERT: {message}")
        if self.email_notifications_enabled:
            self.send_email_alert(message)

    def send_email_alert(self, message):
        try:
            msg = EmailMessage()
            msg.set_content(f"System Alert: {message}")
            msg['Subject'] = 'System Performance Alert'
            msg['From'] = 'noreply@system-monitor.local'
            msg['To'] = ', '.join(self.alert_email_recipients)

            # Replace with your SMTP configuration
            with smtplib.SMTP('localhost') as server:
                server.send_message(msg)

            self.logger.info("Alert email sent successfully.")
        except Exception as e:
            self.logger.error(f"Failed to send alert email: {e}")
