"""Google Calendar auth. Source of truth for the class schedule (recurring
events) and personal events — reads and writes wrapped as tools in
calendar_tools.py.

First-time setup: run `scripts/authorize_calendar.py` once, interactively —
it needs a real browser consent from you. After that, the refresh token in
data/google_token.json keeps this working headless.
"""
from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CREDENTIALS_PATH = DATA_DIR / "google_credentials.json"
TOKEN_PATH = DATA_DIR / "google_token.json"

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def load_credentials() -> Credentials:
    if not TOKEN_PATH.exists():
        raise RuntimeError(
            f"No Google token at {TOKEN_PATH}. Run "
            "`uv run python scripts/authorize_calendar.py` once to authorize."
        )
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json())
    return creds


def get_calendar_service():
    return build("calendar", "v3", credentials=load_credentials())
