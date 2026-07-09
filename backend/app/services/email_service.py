"""Email service — Gmail SMTP primary, SendGrid fallback, console in dev."""
import asyncio
import smtplib
import structlog
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings

log = structlog.get_logger()


def _send_via_gmail(to_email: str, subject: str, html_content: str) -> bool:
    """Synchronous Gmail SMTP send — called via asyncio.to_thread."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"TradeMind AI <{settings.GMAIL_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
        server.sendmail(settings.GMAIL_USER, to_email, msg.as_string())
    return True


async def _send_via_sendgrid(to_email: str, subject: str, html_content: str) -> bool:
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
            json={
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": settings.SENDGRID_FROM_EMAIL, "name": settings.SENDGRID_FROM_NAME},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_content}],
            },
        )
        return resp.status_code == 202


async def send_email(to_email: str, subject: str, html_content: str) -> bool:
    # 1. Gmail SMTP (primary)
    if settings.GMAIL_USER and settings.GMAIL_APP_PASSWORD:
        try:
            await asyncio.to_thread(_send_via_gmail, to_email, subject, html_content)
            log.info("email.sent_gmail", to=to_email, subject=subject)
            return True
        except Exception as e:
            log.error("email.gmail_failed", error=str(e))

    # 2. SendGrid (fallback)
    if settings.SENDGRID_API_KEY:
        try:
            result = await _send_via_sendgrid(to_email, subject, html_content)
            if result:
                log.info("email.sent_sendgrid", to=to_email)
                return True
        except Exception as e:
            log.error("email.sendgrid_failed", error=str(e))

    # 3. Console fallback (dev)
    log.info("email.dev_mode", to=to_email, subject=subject)
    print(f"\n📧 [DEV EMAIL] To: {to_email}\nSubject: {subject}\n{html_content}\n")
    return True


async def send_otp_email(to_email: str, name: str, otp: str) -> bool:
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#0f172a;color:#f8fafc;padding:32px;border-radius:12px">
      <div style="text-align:center;margin-bottom:24px">
        <h2 style="color:#00ff88;margin:0">TradeMind AI</h2>
        <p style="color:#94a3b8;margin:4px 0 0">Security Verification</p>
      </div>
      <p>Hi {name},</p>
      <p>Your one-time verification code is:</p>
      <div style="text-align:center;margin:28px 0">
        <span style="display:inline-block;background:#1e293b;border:2px solid #00ff88;color:#00ff88;font-size:36px;font-weight:bold;letter-spacing:12px;padding:16px 32px;border-radius:12px">{otp}</span>
      </div>
      <p style="color:#94a3b8;font-size:13px">This code expires in <strong style="color:#f8fafc">10 minutes</strong>. Do not share it with anyone.</p>
      <p style="color:#94a3b8;font-size:13px">If you did not attempt to sign in, please ignore this email.</p>
    </div>
    """
    return await send_email(to_email, "Your TradeMind AI verification code", html)


async def send_verification_email(to_email: str, name: str, token: str) -> bool:
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#0f172a;color:#f8fafc;padding:32px;border-radius:12px">
      <h2 style="color:#00ff88">Verify your TradeMind AI account</h2>
      <p>Hi {name}, thanks for signing up! Click below to verify your email address.</p>
      <a href="{verify_url}" style="display:inline-block;background:linear-gradient(135deg,#00ff88,#00d4ff);color:#000;font-weight:bold;padding:12px 28px;border-radius:8px;text-decoration:none;margin:16px 0">
        Verify Email
      </a>
      <p style="color:#94a3b8;font-size:13px">This link expires in 24 hours. If you didn't create an account, ignore this email.</p>
    </div>
    """
    return await send_email(to_email, "Verify your TradeMind AI email", html)


async def send_password_reset_email(to_email: str, name: str, token: str) -> bool:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#0f172a;color:#f8fafc;padding:32px;border-radius:12px">
      <h2 style="color:#00ff88">Reset your TradeMind AI password</h2>
      <p>Hi {name}, we received a request to reset your password.</p>
      <a href="{reset_url}" style="display:inline-block;background:linear-gradient(135deg,#00ff88,#00d4ff);color:#000;font-weight:bold;padding:12px 28px;border-radius:8px;text-decoration:none;margin:16px 0">
        Reset Password
      </a>
      <p style="color:#94a3b8;font-size:13px">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
    </div>
    """
    return await send_email(to_email, "Reset your TradeMind AI password", html)


async def send_announcement_email(to_email: str, name: str, title: str, message: str) -> bool:
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;background:#0f172a;color:#f8fafc;padding:32px;border-radius:12px">
      <h2 style="color:#00ff88">📢 {title}</h2>
      <p>Hi {name},</p>
      <p>{message}</p>
      <p style="color:#94a3b8;font-size:13px">— The TradeMind AI Team</p>
    </div>
    """
    return await send_email(to_email, f"TradeMind AI: {title}", html)
