import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

from google_auth_oauthlib.flow import Flow
import google.oauth2.credentials
from googleapiclient.discovery import build
import google.auth.transport.requests

from app.config import settings
from app.database import SessionLocal
from app.models.settings import SystemSetting
from app.services.security import encrypt_string, decrypt_string

logger = logging.getLogger(__name__)

def get_google_flow(state: Optional[str] = None) -> Flow:
    """
    Builds the Google OAuth2 flow using client credentials from settings.
    """
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID or "",
            "client_secret": settings.GOOGLE_CLIENT_SECRET or "",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
        }
    }
    scopes = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events"
    ]
    flow = Flow.from_client_config(
        client_config,
        scopes=scopes,
        state=state
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow

def save_google_credentials(credentials: google.oauth2.credentials.Credentials) -> None:
    """
    Serializes and encrypts Google OAuth2 credentials to the database settings table.
    """
    creds_dict = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }
    serialized = json.dumps(creds_dict)
    encrypted = encrypt_string(serialized)

    db = SessionLocal()
    try:
        setting = db.query(SystemSetting).filter(SystemSetting.key == "google_oauth_credentials").first()
        if not setting:
            setting = SystemSetting(key="google_oauth_credentials", value=encrypted)
            db.add(setting)
        else:
            setting.value = encrypted
        db.commit()
    except Exception as e:
        logger.error(f"Failed to encrypt and save Google OAuth credentials: {str(e)}")
        raise e
    finally:
        db.close()

def get_google_credentials_from_db() -> Optional[Dict[str, Any]]:
    """
    Retrieves and decrypts Google OAuth2 credentials from the database settings table.
    """
    db = SessionLocal()
    try:
        setting = db.query(SystemSetting).filter(SystemSetting.key == "google_oauth_credentials").first()
        if not setting:
            return None
        decrypted = decrypt_string(setting.value)
        return json.loads(decrypted)
    except Exception as e:
        logger.error(f"Failed to load/decrypt Google credentials: {str(e)}")
        return None
    finally:
        db.close()

def get_calendar_client() -> Optional[Any]:
    """
    Instantiates a Google Calendar API client using stored credentials,
    automatically handling token refreshing if required.
    """
    creds_dict = get_google_credentials_from_db()
    if not creds_dict:
        return None

    credentials = google.oauth2.credentials.Credentials(
        token=creds_dict.get("token"),
        refresh_token=creds_dict.get("refresh_token"),
        token_uri=creds_dict.get("token_uri"),
        client_id=creds_dict.get("client_id"),
        client_secret=creds_dict.get("client_secret"),
        scopes=creds_dict.get("scopes")
    )

    try:
        if credentials.expired and credentials.refresh_token:
            logger.info("Google access token expired. Attempting token refresh...")
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)
            save_google_credentials(credentials)
            logger.info("Google access token successfully refreshed and saved.")
    except Exception as e:
        logger.error(f"Failed to refresh Google access token: {str(e)}")
        return None

    return build("calendar", "v3", credentials=credentials)

def create_interview_meet_event(
    candidate_name: str,
    candidate_email: str,
    job_title: str,
    start_time_iso: str
) -> Tuple[str, str]:
    """
    Creates a Google Calendar event with auto-generated Google Meet conference details.
    Returns:
        Tuple[str, str]: (google_event_id, meet_link)
    """
    service = get_calendar_client()
    if not service:
        raise ValueError("Google Calendar is not linked. Please connect Google Calendar in settings first.")

    # Parse ISO start time and calculate end time (default 45 minutes)
    try:
        # Standardize UTC formatting
        clean_time = start_time_iso.replace("Z", "+00:00")
        start_time = datetime.fromisoformat(clean_time)
    except Exception as e:
        logger.error(f"Invalid interview start time format: {start_time_iso}")
        raise ValueError(f"Invalid ISO datetime format: {str(e)}")

    end_time = start_time + timedelta(minutes=45)

    event_body = {
        "summary": f"Technical Interview: {candidate_name} — {job_title}",
        "description": f"Video discussion and coding evaluation for the {job_title} role at Visl AI Labs.",
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "UTC"
        },
        "attendees": [
            {"email": candidate_email}
        ],
        "conferenceData": {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {
                    "type": "hangoutsMeet"
                }
            }
        }
    }

    try:
        event = service.events().insert(
            calendarId="primary",
            body=event_body,
            conferenceDataVersion=1
        ).execute()

        event_id = event.get("id")
        meet_link = None

        # Extract generated Google Meet URL
        conf_data = event.get("conferenceData", {})
        entry_points = conf_data.get("entryPoints", [])
        for ep in entry_points:
            if ep.get("entryPointType") == "video":
                meet_link = ep.get("uri")
                break

        if not meet_link:
            logger.warning(f"Google Calendar event created but Meet video link was not generated.")
            meet_link = event.get("htmlLink")  # fallback to calendar event link

        return event_id, meet_link
    except Exception as e:
        logger.error(f"Failed to create Google Calendar event: {str(e)}")
        raise e
