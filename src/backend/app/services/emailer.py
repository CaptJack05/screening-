import smtplib
import json
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy.orm import Session
import uuid

from app.database import SessionLocal
from app.models.settings import SystemSetting
from app.models.email_log import EmailLog
from app.services.security import decrypt_string

logger = logging.getLogger(__name__)

def get_smtp_config() -> Optional[Dict[str, Any]]:
    """
    Decrypted retrieval of SMTP configurations from database.
    """
    db = SessionLocal()
    try:
        setting = db.query(SystemSetting).filter(SystemSetting.key == "smtp_config").first()
        if not setting:
            return None
        decrypted = decrypt_string(setting.value)
        return json.loads(decrypted)
    except Exception as e:
        logger.error(f"Failed to load SMTP settings: {str(e)}")
        return None
    finally:
        db.close()

def send_smtp_email(
    candidate_id: str,
    recipient_email: str,
    subject: str,
    body_html: str,
    email_type: str
) -> bool:
    """
    Sends an email using the stored recruiter SMTP settings.
    Logs success or failure to the email_logs audit table.
    """
    config = get_smtp_config()
    db = SessionLocal()
    
    # 1. Initialize Log Record
    email_log = EmailLog(
        id=str(uuid.uuid4()),
        candidate_id=candidate_id,
        email_type=email_type,
        recipient_email=recipient_email,
        subject=subject,
        body_preview=body_html[:200] + ("..." if len(body_html) > 200 else ""),
        status="FAILED"
    )
    
    if not config:
        logger.error("No SMTP credentials configured. Skipping email delivery.")
        email_log.status = "FAILED"
        db.add(email_log)
        db.commit()
        db.close()
        return False

    try:
        # 2. Build MIME Message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = config["sender_email"]
        msg['To'] = recipient_email
        msg.attach(MIMEText(body_html, 'html'))

        # 3. SMTP Handshake & Authenticate
        host = config["host"]
        port = int(config["port"])
        username = config["username"]
        password = config["password"]

        server = smtplib.SMTP(host, port, timeout=15.0)
        server.ehlo()
        
        # Enable TLS if needed
        if port == 587 or "starttls" in host.lower():
            server.starttls()
            server.ehlo()
            
        server.login(username, password)
        server.sendmail(config["sender_email"], recipient_email, msg.as_string())
        server.quit()

        # Update log status to SENT
        email_log.status = "SENT"
        logger.info(f"Email of type {email_type} sent successfully to {recipient_email}")
        status = True
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
        status = False
        
    db.add(email_log)
    db.commit()
    db.close()
    return status

def render_test_link_email(candidate_name: str, test_url: str) -> str:
    """
    Generates a professional HTML body for candidate aptitude & coding test links.
    """
    return f"""
    <html>
      <body style="font-family: sans-serif; color: #334155; line-height: 1.6; padding: 20px;">
        <div style="max-w: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
          <div style="background-color: #8b5cf6; padding: 24px; text-align: center; color: white;">
            <h2 style="margin: 0; font-size: 22px;">Candidate Assessment Stage</h2>
          </div>
          <div style="padding: 24px;">
            <p>Dear {candidate_name},</p>
            <p>Thank you for your interest in the <strong>Founding AI Engineer</strong> position at Visl AI Labs.</p>
            <p>We are pleased to invite you to the next stage of our recruitment process: a logical aptitude and technical coding assessment.</p>
            <div style="text-align: center; margin: 30px 0;">
              <a href="{test_url}" style="background-color: #8b5cf6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Start Assessment</a>
            </div>
            <p style="font-size: 13px; color: #64748b;">If the button above does not work, please copy and paste this URL into your browser:<br>{test_url}</p>
            <p>Please complete this test within 48 hours. Best of luck!</p>
            <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
            <p style="font-size: 12px; color: #94a3b8; text-align: center;">This is an automated invitation. Do not reply directly to this email.</p>
          </div>
        </div>
      </body>
    </html>
    """

def render_interview_invite_email(candidate_name: str, time_str: str, meet_link: str) -> str:
    """
    Generates a professional HTML body for candidate interview scheduling confirmations.
    """
    return f"""
    <html>
      <body style="font-family: sans-serif; color: #334155; line-height: 1.6; padding: 20px;">
        <div style="max-w: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
          <div style="background-color: #10b981; padding: 24px; text-align: center; color: white;">
            <h2 style="margin: 0; font-size: 22px;">Interview Confirmation</h2>
          </div>
          <div style="padding: 24px;">
            <p>Dear {candidate_name},</p>
            <p>Congratulations! Based on your credentials and test results, you have been shortlisted for interviews.</p>
            <p>Your technical discussion has been successfully scheduled:</p>
            <div style="background-color: #f8fafc; padding: 16px; border-radius: 8px; margin: 20px 0; border: 1px solid #e2e8f0;">
              <p style="margin: 0 0 8px 0;"><strong>Date & Time:</strong> {time_str}</p>
              <p style="margin: 0;"><strong>Video Link:</strong> <a href="{meet_link}" style="color: #10b981; font-weight: bold;">Google Meet Link</a></p>
            </div>
            <p>Please join the meeting link 5 minutes prior to the scheduled time. We look forward to speaking with you!</p>
            <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
            <p style="font-size: 12px; color: #94a3b8; text-align: center;">This is an automated scheduling invitation.</p>
          </div>
        </div>
      </body>
    </html>
    """
