# backend/app/auth/utils.py
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from typing import Dict, Any

from app.config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES
from app.logger import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    hashed = pwd_context.hash(password)
    logger.debug("Password hashed successfully")
    return hashed

def verify_password(plain_password: str, hashed_password: str) -> bool:
    verified = pwd_context.verify(plain_password, hashed_password)
    logger.debug("Password verification result: %s", verified)
    return verified

def create_access_token(data: Dict[str, Any], expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    logger.debug("Access token created")
    return token
