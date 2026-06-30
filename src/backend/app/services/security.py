from cryptography.fernet import Fernet
from app.config import settings
import logging

logger = logging.getLogger(__name__)

_fernet_instance = None

def get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        try:
            # Fernet key must be 32 url-safe base64-encoded bytes
            _fernet_instance = Fernet(settings.ENCRYPTION_KEY.encode())
        except Exception as e:
            logger.error(f"Invalid ENCRYPTION_KEY format. Re-generating key instance: {str(e)}")
            # Fallback placeholder to prevent crashes
            fallback_key = Fernet.generate_key()
            _fernet_instance = Fernet(fallback_key)
    return _fernet_instance

def encrypt_string(text: str) -> str:
    """
    Encrypts a plaintext string.
    """
    if not text:
        return ""
    f = get_fernet()
    return f.encrypt(text.encode("utf-8")).decode("utf-8")

def decrypt_string(encrypted_text: str) -> str:
    """
    Decrypts an encrypted ciphertext string.
    """
    if not encrypted_text:
        return ""
    f = get_fernet()
    return f.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
