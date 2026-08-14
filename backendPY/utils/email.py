import smtplib
import asyncio
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import settings

logger = logging.getLogger("email_util")

def send_smtp_email_sync(to_email: str, subject: str, body_html: str, body_text: str = ""):
    """Synchronous SMTP email sending function to be executed in a separate thread."""
    if not settings.SMTP_USER or not settings.SMTP_PASS:
        logger.warning("SMTP credentials are not configured. Skipping email send.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email

    if body_text:
        msg.attach(MIMEText(body_text, "plain"))
    if body_html:
        msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())
        logger.info(f"Successfully sent email to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        raise e

async def send_extracted_text_email(to_email: str, file_name: str, view_link: str, user_name: str):
    """Sends an email with the link to view the extracted text."""
    from datetime import datetime
    subject = f"Text Extracted Successfully: {file_name}"
    current_year = datetime.now().year
    
    body_text = (
        f"Dear {user_name},\n\n"
        f"The text from your uploaded document, {file_name}, has been successfully extracted and is now ready for your review.\n"
        f"Please click the View Extracted Text button to access the extracted content.\n"
        f"If the button does not work, you may copy and paste the following link into your web browser:\n"
        f"{view_link}\n\n"
        f"Best regards,\n"
        f"DocLens Team\n\n"
        f"This is an automated notification from DocLens. Please do not reply directly to this email."
    )

    body_html = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <title>Text Extraction Complete</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <!--[if mso]>
  <style type="text/css">
    body, table, td, a {{ font-family: Arial, Helvetica, sans-serif !important; }}
  </style>
  <![endif]-->
</head>
<body style="margin: 0; padding: 0; width: 100% !important; background-color: #f3f4f6; font-family: Arial, sans-serif; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f3f4f6; padding: 40px 10px;">
    <tr>
      <td align="center">
        <!-- Main Card -->
        <table border="0" cellpadding="0" cellspacing="0" width="600" style="background-color: #ffffff; border-radius: 8px; border: 1px solid #e5e7eb; border-collapse: separate;">
          
          <!-- Header (Brand/Accent) -->
          <tr>
            <td style="background-color: #4f46e5; padding: 24px; border-top-left-radius: 8px; border-top-right-radius: 8px; text-align: center;">
              <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: bold; letter-spacing: -0.025em;">DocLens</h1>
              <p style="color: #e0e7ff; margin: 4px 0 0 0; font-size: 14px;">Turn documents into knowledge.</p>
            </td>
          </tr>
          
          <!-- Body Content -->
          <tr>
            <td style="padding: 40px 32px; background-color: #ffffff;">
              <p style="color: #111827; font-size: 16px; line-height: 24px; margin-top: 0; margin-bottom: 20px;">
                Dear {user_name},
              </p>
              <p style="color: #4b5563; font-size: 16px; line-height: 24px; margin-bottom: 20px;">
                The text from your uploaded document, <strong>{file_name}</strong>, has been successfully extracted and is now ready for your review.
              </p>
              <p style="color: #4b5563; font-size: 16px; line-height: 24px; margin-bottom: 24px;">
                Please click the View Extracted Text button to access the extracted content.
              </p>
              
              <!-- CTA Button Section -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 32px;">
                <tr>
                  <td align="center">
                    <table border="0" cellpadding="0" cellspacing="0">
                      <tr>
                        <td align="center" bgcolor="#4f46e5" style="border-radius: 6px;">
                          <a href="{view_link}" target="_blank" style="display: inline-block; padding: 14px 28px; font-size: 16px; font-weight: bold; color: #ffffff; text-decoration: none; border-radius: 6px; border: 1px solid #4f46e5;">View Extracted Text</a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              
              <p style="color: #4b5563; font-size: 16px; line-height: 24px; margin-bottom: 8px;">
                Best regards,
              </p>
              <p style="color: #111827; font-size: 16px; font-weight: bold; line-height: 24px; margin-bottom: 24px; margin-top: 0;">
                DocLens Team
              </p>
              
              <!-- Divider -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 24px;">
                <tr>
                  <td style="border-bottom: 1px solid #e5e7eb; height: 1px; line-height: 1px; font-size: 1px;">&nbsp;</td>
                </tr>
              </table>
              
              <!-- Plain text fallback URL -->
              <p style="color: #6b7280; font-size: 12px; line-height: 18px; margin-bottom: 0; word-break: break-all;">
                If the button does not work, you may copy and paste the following link into your web browser:
                <br />
                <a href="{view_link}" style="color: #4f46e5; text-decoration: underline;">{view_link}</a>
              </p>
            </td>
          </tr>
          
          <!-- Footer -->
          <tr>
            <td style="background-color: #f9fafb; padding: 24px 32px; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; border-top: 1px solid #f3f4f6; text-align: center;">
              <p style="color: #9ca3af; font-size: 12px; line-height: 18px; margin: 0;">
                This is an automated notification from DocLens. Please do not reply directly to this email.
              </p>
              <p style="color: #9ca3af; font-size: 12px; line-height: 18px; margin: 8px 0 0 0;">
                &copy; {current_year} DocLens — Turn documents into knowledge. All rights reserved.
              </p>
            </td>
          </tr>
          
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    
    await asyncio.to_thread(send_smtp_email_sync, to_email, subject, body_html, body_text)
