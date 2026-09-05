"""One-time interactive Google Calendar authorization. Run this yourself —
it needs a real browser to grant consent, then saves a refresh token so the
bot can use the calendar headlessly afterward.

Usage: uv run python scripts/authorize_calendar.py
"""
from __future__ import annotations

from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CREDENTIALS_PATH = DATA_DIR / "google_credentials.json"
TOKEN_PATH = DATA_DIR / "google_token.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main() -> None:
    if not CREDENTIALS_PATH.exists():
        raise SystemExit(
            f"Missing {CREDENTIALS_PATH}. Download your OAuth client JSON from "
            "Google Cloud Console and save it there first."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    print(f"Authorized. Token saved to {TOKEN_PATH}.")


if __name__ == "__main__":
    main()
