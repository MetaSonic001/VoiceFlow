from datetime import datetime, timedelta
import os
import jwt
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .models import UserRole
from .db import get_session
from passlib.context import CryptContext

JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')

security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def create_access_token(subject: str, role: str = 'user', expires_minutes: int = 60*24):
    now = datetime.utcnow()
    payload = {
        'sub': subject,
        'role': role,
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(minutes=expires_minutes)).timestamp())
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail='Token expired')
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid token')


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail='Missing credentials')
    payload = decode_access_token(credentials.credentials)
    email = payload.get('sub')
    role = payload.get('role')
    if not email:
        raise HTTPException(status_code=401, detail='Invalid token payload')

    # Return a lightweight user object from the token (avoid DB roundtrip here).
    return {'email': email, 'role': role}


def require_role(required: str):
    async def _dep(user = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail='Unauthorized')
        if user.get('role') != required and user.get('role') != UserRole.admin.value:
            raise HTTPException(status_code=403, detail='Forbidden')
        return user

    return _dep
