import smtplib
import asyncio
import logging
import os
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from core.config import settings

logger = logging.getLogger("email_util")

def get_doclens_logo_path() -> Path:
    """Returns the absolute path to the DocLens logo (favicon.png)."""
    return Path(__file__).resolve().parent.parent.parent / "frontend" / "public" / "favicon.png"

def send_smtp_email_sync(to_email: str, subject: str, body_html: str, body_text: str = "", logo_path: str = None):
    """Synchronous SMTP email sending function with inline CID logo support."""
    if not settings.SMTP_USER or not settings.SMTP_PASS:
        logger.warning("SMTP credentials are not configured. Skipping email send.")
        return

    # Root container 'related' allows inline images (CID) referenced in HTML
    msg_root = MIMEMultipart("related")
    msg_root["Subject"] = subject
    msg_root["From"] = settings.SMTP_FROM
    msg_root["To"] = to_email

    # Alternative container for plain text and HTML
    msg_alt = MIMEMultipart("alternative")
    msg_root.attach(msg_alt)

    if body_text:
        msg_alt.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        msg_alt.attach(MIMEText(body_html, "html", "utf-8"))

    # Resolve logo path
    if not logo_path:
        default_logo = get_doclens_logo_path()
        if default_logo.exists():
            logo_path = str(default_logo)

    # Attach inline logo with Content-ID: <doclens_logo>
    if logo_path and os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f:
                img_data = f.read()
            msg_img = MIMEImage(img_data, _subtype="png")
            msg_img.add_header("Content-ID", "<doclens_logo>")
            msg_img.add_header("Content-Disposition", "inline", filename="favicon.png")
            msg_root.attach(msg_img)
        except Exception as img_err:
            logger.warning(f"Could not attach inline logo to email: {img_err}")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_FROM, to_email, msg_root.as_string())
        logger.info(f"Successfully sent email to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        raise e

async def send_extracted_text_email(to_email: str, file_name: str, view_link: str, user_name: str):
    """Sends an email with the DocLens logo and link to view the extracted text."""
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
    body, table, td, a {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important; }}
  </style>
  <![endif]-->
</head>
<body style="margin: 0; padding: 0; width: 100% !important; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f8fafc; padding: 48px 12px;">
    <tr>
      <td align="center">
        <!-- Main Card Container -->
        <table border="0" cellpadding="0" cellspacing="0" width="560" style="max-width: 560px; width: 100%; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; border-collapse: separate; box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.05); overflow: hidden;">
          
          <!-- Header Bar: Logo on Left + Status Badge on Right -->
          <tr>
            <td style="padding: 24px 32px; border-bottom: 1px solid #f1f5f9; background-color: #ffffff;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <!-- Left: Brand Logo & Title -->
                  <td align="left" valign="middle">
                    <table border="0" cellpadding="0" cellspacing="0">
                      <tr>
                        <td valign="middle" style="padding-right: 12px;">
                          <img src="cid:doclens_logo" alt="DocLens Logo" width="36" height="36" style="display: block; width: 36px; height: 36px; border: 0; outline: none; text-decoration: none;" />
                        </td>
                        <td valign="middle">
                          <span style="font-size: 18px; font-weight: 700; color: #0f172a; letter-spacing: -0.02em; display: block; line-height: 1.2;">DocLens</span>
                          <span style="font-size: 11px; font-weight: 500; color: #64748b; letter-spacing: 0.01em;">Document Intelligence</span>
                        </td>
                      </tr>
                    </table>
                  </td>
                  <!-- Right: Status Badge -->
                  <td align="right" valign="middle">
                    <table border="0" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="background-color: #ecfdf5; border: 1px solid #a7f3d0; padding: 4px 10px; border-radius: 20px;">
                          <span style="color: #059669; font-size: 11px; font-weight: 600;">
                            &#10003; Extracted
                          </span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          
          <!-- Body Content Area -->
          <tr>
            <td style="padding: 32px 32px 28px 32px; background-color: #ffffff;">
              
              <!-- Greeting & Headline -->
              <h1 style="color: #0f172a; font-size: 22px; font-weight: 700; line-height: 30px; margin: 0 0 8px 0; letter-spacing: -0.02em;">
                Your document is ready
              </h1>
              
              <p style="color: #475569; font-size: 15px; line-height: 24px; margin: 0 0 24px 0;">
                Hi {user_name}, we've successfully processed and extracted the text and layout from your uploaded file.
              </p>

              <!-- File Information Card -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; margin-bottom: 24px;">
                <tr>
                  <td style="padding: 16px 18px;">
                    <table border="0" cellpadding="0" cellspacing="0" width="100%">
                      <tr>
                        <td width="36" valign="middle" style="padding-right: 14px;">
                          <div style="background-color: #eff6ff; border: 1px solid #dbeafe; width: 36px; height: 36px; border-radius: 8px; text-align: center; line-height: 36px; font-size: 16px;">
                            📄
                          </div>
                        </td>
                        <td valign="middle">
                          <p style="margin: 0; font-size: 14px; font-weight: 600; color: #0f172a; word-break: break-all; line-height: 20px;">
                            {file_name}
                          </p>
                          <p style="margin: 2px 0 0 0; font-size: 12px; color: #64748b; line-height: 16px;">
                            Status: <span style="color: #059669; font-weight: 600;">Processing Complete</span>
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- What You Can Do (Quick Features) -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 28px;">
                <tr>
                  <td style="color: #334155; font-size: 13px; line-height: 22px;">
                    <div style="margin-bottom: 6px;">
                      <span style="color: #4f46e5; font-weight: bold; margin-right: 6px;">&bull;</span> <strong>Interactive Viewer:</strong> Inspect pages and text side-by-side.
                    </div>
                    <div style="margin-bottom: 6px;">
                      <span style="color: #4f46e5; font-weight: bold; margin-right: 6px;">&bull;</span> <strong>AI Assistant:</strong> Query document content and get instant answers.
                    </div>
                    <div>
                      <span style="color: #4f46e5; font-weight: bold; margin-right: 6px;">&bull;</span> <strong>Quick Export:</strong> Copy raw extracts or save directly to projects.
                    </div>
                  </td>
                </tr>
              </table>
              
              <!-- Primary CTA Button -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 28px;">
                <tr>
                  <td align="left">
                    <table border="0" cellpadding="0" cellspacing="0">
                      <tr>
                        <td align="center" bgcolor="#4f46e5" style="border-radius: 8px; background-color: #4f46e5;">
                          <a href="{view_link}" target="_blank" style="display: inline-block; padding: 13px 28px; font-size: 14px; font-weight: 600; color: #ffffff; text-decoration: none; border-radius: 8px; border: 1px solid #4f46e5; letter-spacing: 0.01em;">
                            View Extracted Document &rarr;
                          </a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              
              <!-- Sign off -->
              <p style="color: #64748b; font-size: 13px; line-height: 20px; margin: 0 0 2px 0;">
                Best regards,
              </p>
              <p style="color: #0f172a; font-size: 14px; font-weight: 600; line-height: 20px; margin: 0 0 24px 0;">
                The DocLens Team
              </p>
              
              <!-- Subtle Divider Line -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 20px;">
                <tr>
                  <td style="border-bottom: 1px solid #f1f5f9; height: 1px; line-height: 1px; font-size: 1px;">&nbsp;</td>
                </tr>
              </table>
              
              <!-- Fallback Direct Link -->
              <p style="color: #94a3b8; font-size: 11px; line-height: 16px; margin: 0; word-break: break-all;">
                If the button above does not work, copy and paste this URL into your browser:
                <br />
                <a href="{view_link}" style="color: #4f46e5; text-decoration: underline; word-break: break-all;">{view_link}</a>
              </p>
            </td>
          </tr>
          
          <!-- Clean Footer Area -->
          <tr>
            <td style="background-color: #f8fafc; padding: 20px 32px; border-top: 1px solid #f1f5f9; text-align: center;">
              <p style="color: #94a3b8; font-size: 11px; line-height: 16px; margin: 0;">
                This is an automated notification from DocLens. Please do not reply directly to this email.
              </p>
              <p style="color: #94a3b8; font-size: 11px; line-height: 16px; margin: 4px 0 0 0;">
                &copy; {current_year} DocLens. All rights reserved.
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



