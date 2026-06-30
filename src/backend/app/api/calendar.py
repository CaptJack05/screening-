from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.services.calendar import get_google_flow, save_google_credentials, get_google_credentials_from_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendar", tags=["Calendar"])

@router.get("/auth")
def auth_google_calendar():
    """
    Initiates Google OAuth2 consent screen redirect.
    """
    try:
        flow = get_google_flow()
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"
        )
        return RedirectResponse(url=authorization_url)
    except Exception as e:
        logger.error(f"Failed to generate Google auth URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Google OAuth initialization failed: {str(e)}")

@router.get("/callback")
def google_calendar_callback(request: Request):
    """
    Receives code and state query parameters from Google, exchanges them,
    encrypts credentials, and saves them. Returns HTML that closes the OAuth popup window.
    """
    code = request.query_params.get("code")
    error = request.query_params.get("error")

    if error:
        logger.error(f"Google OAuth callback error received: {error}")
        return HTMLResponse(
            content=f"""
            <html>
              <body style="font-family: sans-serif; text-align: center; padding: 40px; background-color: #020617; color: #f43f5e;">
                <h2>Authentication Failed</h2>
                <p>Google returned error: {error}</p>
                <button onclick="window.close()" style="padding: 10px 20px; background-color: #f43f5e; color: white; border: none; border-radius: 6px; cursor: pointer;">Close Window</button>
              </body>
            </html>
            """,
            status_code=400
        )

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code.")

    try:
        flow = get_google_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials

        if not credentials.refresh_token:
            logger.warning("No refresh token returned. This happens if authorization is already approved. Forcing consent screen next time.")

        save_google_credentials(credentials)
        logger.info("Recruiter Google Calendar linked successfully.")

        # Sleek auto-closing success page that sends a postMessage back to the React parent dashboard
        return HTMLResponse(
            content="""
            <html>
              <head>
                <script>
                  if (window.opener) {
                    window.opener.postMessage("google-calendar-connected", "*");
                  }
                  setTimeout(function() {
                    window.close();
                  }, 1500);
                </script>
              </head>
              <body style="font-family: sans-serif; text-align: center; padding: 40px; background-color: #020617; color: #f8fafc; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 80vh;">
                <div style="border: 2px solid #10b981; padding: 24px; border-radius: 16px; background-color: #064e3b/20; max-w: 400px;">
                  <h2 style="color: #34d399; margin-top: 0;">Google Calendar Connected!</h2>
                  <p style="color: #94a3b8; font-size: 14px;">The credentials have been successfully encrypted and saved to the database.</p>
                  <p style="color: #64748b; font-size: 12px; margin-bottom: 0;">This window will close automatically...</p>
                </div>
              </body>
            </html>
            """
        )
    except Exception as e:
        logger.error(f"Error during Google OAuth code exchange: {str(e)}")
        return HTMLResponse(
            content=f"""
            <html>
              <body style="font-family: sans-serif; text-align: center; padding: 40px; background-color: #020617; color: #f43f5e;">
                <h2>Authentication Exchange Failed</h2>
                <p>Failed to exchange Google OAuth authorization code: {str(e)}</p>
                <button onclick="window.close()" style="padding: 10px 20px; background-color: #f43f5e; color: white; border: none; border-radius: 6px; cursor: pointer;">Close Window</button>
              </body>
            </html>
            """,
            status_code=500
        )

@router.get("/status")
def google_calendar_status():
    """
    Returns connection status of Google Calendar.
    """
    try:
        creds = get_google_credentials_from_db()
        return {
            "connected": creds is not None,
            "scopes": creds.get("scopes", []) if creds else []
        }
    except Exception as e:
        logger.error(f"Failed to fetch Google Calendar connection status: {str(e)}")
        return {"connected": False, "error": str(e)}
