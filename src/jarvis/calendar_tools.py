"""Calendar tools. Reads (list events) are unrestricted — no side effect.
Writes (add/update/delete) are this project's first tool with a real-world
side effect, so each takes confirm: bool = False and, unconfirmed, returns a
preview instead of executing. This is a stopgap, not the real safety gate
(4.5) — that's the next thing to build now that a write-tool exists to gate.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from langchain_core.tools import tool

from .calendar_service import get_calendar_service
from .config import load_settings


def _event_summary(event: dict) -> dict:
    start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date"))
    end = event.get("end", {}).get("dateTime", event.get("end", {}).get("date"))
    return {
        "id": event["id"],
        "title": event.get("summary", "(no title)"),
        "start": start,
        "end": end,
    }


@tool
def list_calendar_events(days_ahead: int = 7) -> list[dict]:
    """List calendar events (including recurring ones like classes, expanded
    into individual instances) from now through the next N days. Default 7."""
    service = get_calendar_service()
    now = datetime.now().astimezone()
    time_max = now + timedelta(days=days_ahead)
    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return [_event_summary(e) for e in result.get("items", [])]


@tool
def add_calendar_event(
    title: str, start_datetime: str, end_datetime: str, confirm: bool = False
) -> dict:
    """Add a personal calendar event. start_datetime/end_datetime are ISO
    'YYYY-MM-DDTHH:MM:SS' in the user's local timezone (no offset needed).
    This has a real-world side effect: call once with confirm=false to
    preview, tell the user what you're about to do, and only call again with
    confirm=true after they say yes."""
    preview = {"title": title, "start": start_datetime, "end": end_datetime}
    if not confirm:
        return {"pending": True, "action": "add_calendar_event", **preview}

    timezone = load_settings().timezone
    service = get_calendar_service()
    event = (
        service.events()
        .insert(
            calendarId="primary",
            body={
                "summary": title,
                "start": {"dateTime": start_datetime, "timeZone": timezone},
                "end": {"dateTime": end_datetime, "timeZone": timezone},
            },
        )
        .execute()
    )
    return {"created": True, **_event_summary(event)}


@tool
def update_calendar_event(
    event_id: str,
    title: str = "",
    start_datetime: str = "",
    end_datetime: str = "",
    confirm: bool = False,
) -> dict:
    """Update a calendar event (get event_id from list_calendar_events).
    Leave a field empty to keep it unchanged. Real-world side effect: preview
    with confirm=false first, execute with confirm=true only after the user
    agrees."""
    preview = {
        "event_id": event_id,
        "title": title or None,
        "start": start_datetime or None,
        "end": end_datetime or None,
    }
    if not confirm:
        return {"pending": True, "action": "update_calendar_event", **preview}

    timezone = load_settings().timezone
    service = get_calendar_service()
    event = service.events().get(calendarId="primary", eventId=event_id).execute()
    if title:
        event["summary"] = title
    if start_datetime:
        event["start"] = {"dateTime": start_datetime, "timeZone": timezone}
    if end_datetime:
        event["end"] = {"dateTime": end_datetime, "timeZone": timezone}
    updated = (
        service.events().update(calendarId="primary", eventId=event_id, body=event).execute()
    )
    return {"updated": True, **_event_summary(updated)}


@tool
def delete_calendar_event(event_id: str, confirm: bool = False) -> dict:
    """Permanently delete a calendar event (get event_id from
    list_calendar_events). Real-world side effect: preview with confirm=false
    first, execute with confirm=true only after the user agrees."""
    if not confirm:
        return {"pending": True, "action": "delete_calendar_event", "event_id": event_id}

    service = get_calendar_service()
    service.events().delete(calendarId="primary", eventId=event_id).execute()
    return {"deleted": True, "event_id": event_id}


CALENDAR_TOOLS = [
    list_calendar_events,
    add_calendar_event,
    update_calendar_event,
    delete_calendar_event,
]
