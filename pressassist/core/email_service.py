"""Email service for ChelCheleh.

Handles sending emails for password reset, notifications, etc.
Uses built-in smtplib, no external dependencies required.
"""

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .storage import Storage

logger = logging.getLogger(__name__)


class EmailError(Exception):
    """Email sending error."""

    pass


class EmailService:
    """Service for sending emails via SMTP.

    Features:
    - SMTP with TLS support
    - HTML and plain text emails
    - Template-based emails
    - Graceful fallback when SMTP not configured
    """

    def __init__(self, storage: "Storage"):
        """Initialize email service.

        Args:
            storage: Storage instance to read SMTP config.
        """
        self._storage = storage

    def _get_smtp_config(self) -> dict | None:
        """Get SMTP configuration from storage.

        Returns:
            Dict with SMTP settings or None if not configured.
        """
        host = self._storage.get("config.smtp_host")
        if not host:
            return None

        return {
            "host": host,
            "port": self._storage.get("config.smtp_port") or 587,
            "user": self._storage.get("config.smtp_user"),
            "password": self._storage.get("config.smtp_password_encrypted"),
            "from_email": self._storage.get("config.smtp_from_email"),
            "use_tls": self._storage.get("config.smtp_use_tls", True),
        }

    def is_configured(self) -> bool:
        """Check if SMTP is properly configured.

        Returns:
            True if all required SMTP settings are present.
        """
        config = self._get_smtp_config()
        if not config:
            return False

        required = ["host", "user", "password", "from_email"]
        return all(config.get(key) for key in required)

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> bool:
        """Send an email.

        Args:
            to_email: Recipient email address.
            subject: Email subject.
            html_body: HTML content of the email.
            text_body: Plain text fallback (optional).

        Returns:
            True if email sent successfully.

        Raises:
            EmailError: If SMTP not configured or sending fails.
        """
        config = self._get_smtp_config()
        if not config:
            raise EmailError("SMTP not configured")

        required = ["host", "user", "password", "from_email"]
        missing = [key for key in required if not config.get(key)]
        if missing:
            raise EmailError(f"Missing SMTP config: {', '.join(missing)}")

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config["from_email"]
        msg["To"] = to_email

        # Attach text and HTML parts
        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            # Create secure connection
            if config["use_tls"]:
                context = ssl.create_default_context()
                with smtplib.SMTP(config["host"], config["port"]) as server:
                    server.starttls(context=context)
                    server.login(config["user"], config["password"])
                    server.sendmail(config["from_email"], to_email, msg.as_string())
            else:
                with smtplib.SMTP(config["host"], config["port"]) as server:
                    server.login(config["user"], config["password"])
                    server.sendmail(config["from_email"], to_email, msg.as_string())

            logger.info(f"Email sent to {to_email}: {subject}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            raise EmailError("SMTP authentication failed")
        except smtplib.SMTPRecipientsRefused as e:
            logger.error(f"Recipient refused: {e}")
            raise EmailError(f"Invalid recipient: {to_email}")
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            raise EmailError(f"Failed to send email: {e}")
        except Exception as e:
            logger.error(f"Unexpected email error: {e}")
            raise EmailError(f"Email error: {e}")

    def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        reset_url: str,
        site_title: str,
    ) -> bool:
        """Send password reset email.

        Args:
            to_email: User's email address.
            username: User's username.
            reset_url: Full URL for password reset.
            site_title: Name of the website.

        Returns:
            True if sent successfully.
        """
        subject = f"Password Reset - {site_title}"

        html_body = f"""
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Tahoma, Arial, sans-serif; direction: rtl; text-align: right; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
        .button {{ display: inline-block; background: #667eea; color: white !important; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #6c757d; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{site_title}</h1>
        </div>
        <div class="content">
            <h2>بازیابی رمز عبور</h2>
            <p>سلام <strong>{username}</strong>،</p>
            <p>درخواست بازیابی رمز عبور برای حساب کاربری شما ثبت شده است.</p>
            <p>برای تنظیم رمز عبور جدید، روی دکمه زیر کلیک کنید:</p>
            <p style="text-align: center;">
                <a href="{reset_url}" class="button">تنظیم رمز عبور جدید</a>
            </p>
            <p><small>این لینک تا ۱ ساعت معتبر است.</small></p>
            <p><small>اگر شما این درخواست را نداده‌اید، این ایمیل را نادیده بگیرید.</small></p>
        </div>
        <div class="footer">
            <p>&copy; {site_title}</p>
        </div>
    </div>
</body>
</html>
"""

        text_body = f"""
بازیابی رمز عبور - {site_title}

سلام {username}،

درخواست بازیابی رمز عبور برای حساب کاربری شما ثبت شده است.

برای تنظیم رمز عبور جدید، به آدرس زیر بروید:
{reset_url}

این لینک تا ۱ ساعت معتبر است.

اگر شما این درخواست را نداده‌اید، این ایمیل را نادیده بگیرید.
"""

        return self.send_email(to_email, subject, html_body, text_body)

    def send_welcome_email(
        self,
        to_email: str,
        username: str,
        site_title: str,
        login_url: str,
    ) -> bool:
        """Send welcome email after registration.

        Args:
            to_email: User's email address.
            username: User's username.
            site_title: Name of the website.
            login_url: URL to login page.

        Returns:
            True if sent successfully.
        """
        subject = f"Welcome to {site_title}"

        html_body = f"""
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Tahoma, Arial, sans-serif; direction: rtl; text-align: right; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
        .button {{ display: inline-block; background: #667eea; color: white !important; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #6c757d; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{site_title}</h1>
        </div>
        <div class="content">
            <h2>خوش آمدید!</h2>
            <p>سلام <strong>{username}</strong>،</p>
            <p>حساب کاربری شما با موفقیت ایجاد شد.</p>
            <p>اکنون می‌توانید وارد شوید و از امکانات سایت استفاده کنید.</p>
            <p style="text-align: center;">
                <a href="{login_url}" class="button">ورود به سایت</a>
            </p>
        </div>
        <div class="footer">
            <p>&copy; {site_title}</p>
        </div>
    </div>
</body>
</html>
"""

        text_body = f"""
خوش آمدید به {site_title}!

سلام {username}،

حساب کاربری شما با موفقیت ایجاد شد.

برای ورود به سایت به آدرس زیر بروید:
{login_url}
"""

        return self.send_email(to_email, subject, html_body, text_body)

    def send_verification_approved_email(
        self,
        to_email: str,
        username: str,
        site_title: str,
        profile_url: str,
    ) -> bool:
        """Send email when verification is approved.

        Args:
            to_email: User's email address.
            username: User's username.
            site_title: Name of the website.
            profile_url: URL to user's profile.

        Returns:
            True if sent successfully.
        """
        subject = f"Verification Approved - {site_title}"

        html_body = f"""
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Tahoma, Arial, sans-serif; direction: rtl; text-align: right; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
        .button {{ display: inline-block; background: #667eea; color: white !important; padding: 12px 30px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .badge {{ display: inline-block; background: #1DA1F2; color: white; padding: 4px 12px; border-radius: 20px; font-size: 14px; }}
        .footer {{ text-align: center; color: #6c757d; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{site_title}</h1>
        </div>
        <div class="content">
            <h2>تایید هویت انجام شد! <span class="badge">✓</span></h2>
            <p>سلام <strong>{username}</strong>،</p>
            <p>تبریک! حساب کاربری شما تایید شد و اکنون نشان تایید هویت در پروفایل شما نمایش داده می‌شود.</p>
            <p style="text-align: center;">
                <a href="{profile_url}" class="button">مشاهده پروفایل</a>
            </p>
        </div>
        <div class="footer">
            <p>&copy; {site_title}</p>
        </div>
    </div>
</body>
</html>
"""

        text_body = f"""
تایید هویت انجام شد! - {site_title}

سلام {username}،

تبریک! حساب کاربری شما تایید شد و اکنون نشان تایید هویت در پروفایل شما نمایش داده می‌شود.

برای مشاهده پروفایل به آدرس زیر بروید:
{profile_url}
"""

        return self.send_email(to_email, subject, html_body, text_body)
