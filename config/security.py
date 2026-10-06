import hashlib
import secrets

def hash_password(password: str) -> str:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with a secure random salt.
    Format: pbkdf2_sha256$iterations$salt$hash
    """
    if not password:
        password = ""
    salt = secrets.token_hex(16)
    iterations = 200_000
    derived = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${derived}"

def verify_password(password: str, hashed_value: str) -> bool:
    """Verifies a plain password against the stored pbkdf2_sha256 hash."""
    if not password or not hashed_value:
        return False
    try:
        parts = hashed_value.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = parts[2]
        expected_derived = parts[3]
        
        actual_derived = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        ).hex()
        
        return secrets.compare_digest(actual_derived, expected_derived)
    except Exception:
        return False
