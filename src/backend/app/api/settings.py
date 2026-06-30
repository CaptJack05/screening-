from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import json
import smtplib

from app.database import get_db
from app.models.settings import SystemSetting
from app.services.security import encrypt_string, decrypt_string

router = APIRouter(prefix="/api/settings", tags=["Settings"])

class SMTPSettings(BaseModel):
    host: str
    port: int
    username: str
    password: str
    sender_email: str

@router.post("/smtp")
def save_smtp_settings(config: SMTPSettings, db: Session = Depends(get_db)):
    """
    Saves SMTP credentials encrypted in the database.
    """
    try:
        config_dict = config.model_dump()
        serialized = json.dumps(config_dict)
        encrypted = encrypt_string(serialized)
        
        # Save to database
        setting = db.query(SystemSetting).filter(SystemSetting.key == "smtp_config").first()
        if not setting:
            setting = SystemSetting(key="smtp_config", value=encrypted)
            db.add(setting)
        else:
            setting.value = encrypted
            
        db.commit()
        return {"status": "success", "message": "SMTP settings saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

@router.get("/smtp")
def get_smtp_settings(db: Session = Depends(get_db)):
    """
    Retrieves SMTP settings, masking the password.
    """
    setting = db.query(SystemSetting).filter(SystemSetting.key == "smtp_config").first()
    if not setting:
        return {
            "configured": False,
            "host": "",
            "port": 587,
            "username": "",
            "sender_email": ""
        }
        
    try:
        decrypted = decrypt_string(setting.value)
        config_dict = json.loads(decrypted)
        # Mask password
        config_dict["password"] = "••••••••"
        config_dict["configured"] = True
        return config_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to load and decrypt SMTP settings.")

@router.post("/smtp/test")
def test_smtp_connection(config: SMTPSettings):
    """
    Validates the SMTP credentials by attempting a connection handshake.
    """
    try:
        # SMTP connection handshake check
        server = smtplib.SMTP(config.host, config.port, timeout=10.0)
        server.ehlo()
        if config.port == 587 or "starttls" in config.host.lower():
            server.starttls()
            server.ehlo()
        server.login(config.username, config.password)
        server.quit()
        return {"status": "success", "message": "Successfully connected and authenticated with SMTP server."}
    except Exception as e:
        return {"status": "error", "message": f"SMTP Authentication failed: {str(e)}"}
