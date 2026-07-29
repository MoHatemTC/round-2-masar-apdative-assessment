import os
import resend
from supabase import AsyncClient
import asyncio
import logging
from dotenv import load_dotenv

# 1. Force Python to read the .env file FIRST
load_dotenv()

# 2. Now it will successfully find the key
resend.api_key = os.environ.get("RESEND_API_KEY")
logger = logging.getLogger(__name__)

async def _log_email(db: AsyncClient, recipient: str, subject: str, status: str, error_detail: str = None):
    try:
        await db.table("email_logs").insert({
            "recipient": recipient,
            "subject": subject,
            "status": status,
            "error_detail": error_detail
        }).execute()
    except Exception as e:
        logger.error(f"Failed to write to email_logs: {e}")

async def _send_with_retry(db: AsyncClient, to: str, subject: str, html_content: str, max_retries: int = 3):
    attempt = 0
    success = False
    last_error = None

    while attempt < max_retries and not success:
        attempt += 1
        try:
            resend.Emails.send({
                "from": os.environ.get("EMAIL_FROM", "onboarding@resend.dev"),
                "to": to,
                "subject": subject,
                "html": html_content
            })
            success = True
            await _log_email(db, to, subject, "success")
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Email send failed (attempt {attempt}): {last_error}")
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)

    if not success:
        await _log_email(db, to, subject, "failed", last_error)

async def send_invitation_background(db: AsyncClient, to: str, token: str, base_url: str):
    invite_link = f"{base_url}/assess?token={token}"
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Assessment Invitation</h2>
        <p>You have been invited to complete a competency assessment.</p>
        <a href="{invite_link}" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: #ffffff; text-decoration: none; border-radius: 5px;">Start Assessment</a>
    </div>
    """
    await _send_with_retry(db, to, "Assessment Invitation", html)

async def send_report_background(db: AsyncClient, to: str, overall_pct: float, band: str, is_low_confidence: bool):
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Your Assessment Report</h2>
        <p><strong>Overall Score:</strong> {overall_pct}%</p>
        <p><strong>Competency Band:</strong> {band}</p>
    """
    if is_low_confidence:
        html += '<p style="color: #d9534f;"><em>Note: These results are marked as low confidence due to early termination or insufficient data.</em></p>'
    
    html += "</div>"
    await _send_with_retry(db, to, "Your Assessment Results", html)

async def send_admin_notification_background(db: AsyncClient, admin_email: str, session_id: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Assessment Completed</h2>
        <p>A candidate has finalized their session (ID: {session_id}).</p>
        <p>Log in to the admin dashboard to review the full results.</p>
    </div>
    """
    await _send_with_retry(db, admin_email, f"Session Finalized - {session_id}", html)