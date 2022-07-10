from secrets import token_hex
from datetime import datetime

AUTH_SECRET_KEY: str = token_hex(2048)
AUTH_ALGORITHM: str = "HS256"
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
AUTH_REFRESH_TOKEN_EXPIRE_DAYS: int = AUTH_ACCESS_TOKEN_EXPIRE_MINUTES

AUTH_EMAIL_VERIFICATION_EMAIL_BODY: str= """
Hi {username},

Please click on this link to confirm your email for the AnonLearn platform:
{site_url}

Kind Regards,
{system_username}
""".strip()