"""Notification services — email and Slack."""

import os
from typing import List, Optional


def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email notification."""
    # In production, this would use SMTP
    print(f"[EMAIL] To: {to}, Subject: {subject}")
    return True


def send_slack(message: str, channel: str = "#general") -> bool:
    """Send a Slack notification."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print(f"[SLACK] {channel}: {message}")
        return True

    import requests

    try:
        response = requests.post(
            webhook_url,
            json={
                "text": message,
                "channel": channel,
            },
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send Slack message: {e}")
        return False


def notify_task_assigned(task_id: int, user_id: int):
    """Notify a user that a task has been assigned to them."""
    from models import User
    from database import get_connection

    conn = get_connection()
    try:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

        if user:
            send_email(
                user["email"],
                "New Task Assigned",
                f"Task #{task_id} has been assigned to you.",
            )
    finally:
        conn.close()
