"""
Alert Service
Handles alert creation and notifications (email, Slack)
"""

import smtplib
import requests
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from utils.database import get_db_connection

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'True').lower() == 'true'
        self.alert_email_from = os.getenv('ALERT_EMAIL_FROM')
        self.alert_email_to = os.getenv('ALERT_EMAIL_TO')
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.slack_enabled = os.getenv('SLACK_ENABLED', 'False').lower() == 'true'
        self.alert_cooldown = int(os.getenv('ALERT_COOLDOWN', 300))
    
    def create_alert(self, monitor_id, monitor_name, alert_type, message):
        """Create a new alert and send notifications"""
        
        # Check cooldown period
        if not self.check_cooldown(monitor_id):
            logger.info(f"Alert for monitor {monitor_id} in cooldown period, skipping")
            return None
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Create alert in database
            cur.execute("""
                INSERT INTO alerts (monitor_id, alert_type, message, status)
                VALUES (%s, %s, %s, 'active')
                RETURNING id, created_at
            """, (monitor_id, alert_type, message))
            
            alert = cur.fetchone()
            conn.commit()
            
            alert_id = alert['id']
            created_at = alert['created_at']
            
            logger.warning(f"Alert created: {alert_id} - {message}")
            
            # Send notifications
            self.send_email_alert(monitor_name, alert_type, message, created_at)
            
            if self.slack_enabled and self.slack_webhook:
                self.send_slack_alert(monitor_name, alert_type, message, created_at)
            
            return alert_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating alert: {str(e)}")
            return None
        finally:
            cur.close()
            conn.close()
    
    def check_cooldown(self, monitor_id):
        """Check if enough time has passed since last alert"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cooldown_time = datetime.utcnow() - timedelta(seconds=self.alert_cooldown)
            
            cur.execute("""
                SELECT id FROM alerts
                WHERE monitor_id = %s 
                AND created_at > %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (monitor_id, cooldown_time))
            
            recent_alert = cur.fetchone()
            return recent_alert is None
            
        except Exception as e:
            logger.error(f"Error checking cooldown: {str(e)}")
            return True  # Allow alert if check fails
        finally:
            cur.close()
            conn.close()
    
    def send_email_alert(self, monitor_name, alert_type, message, created_at):
        """Send email notification"""
        if not all([self.smtp_host, self.smtp_user, self.smtp_password, 
                   self.alert_email_from, self.alert_email_to]):
            logger.warning("Email configuration incomplete, skipping email alert")
            return
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🚨 Alert: {monitor_name} is {alert_type}"
            msg['From'] = self.alert_email_from
            msg['To'] = self.alert_email_to
            
            # Create email body
            text_body = f"""
System Monitor Alert

Monitor: {monitor_name}
Status: {alert_type.upper()}
Time: {created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

Message: {message}

---
This is an automated alert from System Monitor
"""
            
            html_body = f"""
<html>
<head></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
        <h2 style="color: #d32f2f; margin-bottom: 20px;">🚨 System Monitor Alert</h2>
        
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Monitor:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{monitor_name}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Status:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; color: #d32f2f; font-weight: bold;">{alert_type.upper()}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Time:</strong></td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
            </tr>
        </table>
        
        <div style="margin-top: 20px; padding: 15px; background-color: #f5f5f5; border-radius: 4px;">
            <strong>Message:</strong><br>
            {message}
        </div>
        
        <p style="margin-top: 20px; font-size: 12px; color: #666;">
            This is an automated alert from System Monitor
        </p>
    </div>
</body>
</html>
"""
            
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email alert sent for {monitor_name}")
            
        except Exception as e:
            logger.error(f"Error sending email alert: {str(e)}")
    
    def send_slack_alert(self, monitor_name, alert_type, message, created_at):
        """Send Slack notification"""
        if not self.slack_webhook:
            return
        
        try:
            color = '#d32f2f' if alert_type == 'down' else '#ffa000'
            
            payload = {
                "text": f"🚨 System Monitor Alert: {monitor_name}",
                "attachments": [{
                    "color": color,
                    "fields": [
                        {
                            "title": "Monitor",
                            "value": monitor_name,
                            "short": True
                        },
                        {
                            "title": "Status",
                            "value": alert_type.upper(),
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
                            "short": False
                        },
                        {
                            "title": "Message",
                            "value": message,
                            "short": False
                        }
                    ],
                    "footer": "System Monitor",
                    "ts": int(created_at.timestamp())
                }]
            }
            
            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Slack alert sent for {monitor_name}")
            
        except Exception as e:
            logger.error(f"Error sending Slack alert: {str(e)}")
