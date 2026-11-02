import os
from datetime import datetime, timezone, timedelta
from typing import List
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from schemas import CalendarEvent

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

def authenticate_google_calendar():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"'{CREDENTIALS_FILE}' not found. Ensure your Desktop OAuth client is in the folder.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)

def get_upcoming_events(lookahead_hours: int = 24) -> List[CalendarEvent]:
    service = authenticate_google_calendar()
    now = datetime.now(timezone.utc)
    time_max = now + timedelta(hours=lookahead_hours)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=time_max.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    raw_items = events_result.get("items", [])
    events: List[CalendarEvent] = []

    for item in raw_items:
        start_raw = item["start"].get("dateTime")
        if not start_raw:
            continue

        event = CalendarEvent(
            title=item.get("summary", "Untitled Event"),
            start_time=datetime.fromisoformat(start_raw),
            location_raw=item.get("location"),
            description=item.get("description"),
        )
        events.append(event)
    return events