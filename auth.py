import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from database import SessionLocal  # also loads the .env file
import models

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is missing. Add a SECRET_KEY line to your .env file.")
ALGORITHM = "HS256"
TOKEN_HOURS = 24

router = APIRouter(prefix="/auth", tags=["Login"])
bearer = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def valid_email(v: str) -> str:
    v = v.strip().lower()
    if "@" not in v or "." not in v.split("@")[-1]:
        raise ValueError("enter a valid email")
    return v


class SignupIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str
    mobile: str
    password: str = Field(min_length=8, max_length=64)

    @field_validator("email")
    @classmethod
    def check_email(cls, v):
        return valid_email(v)

    @field_validator("mobile")
    @classmethod
    def check_mobile(cls, v):
        v = v.strip()
        if not (v.isdigit() and len(v) == 10):
            raise ValueError("mobile must be 10 digits")
        return v


class LoginIn(BaseModel):
    email: str
    password: str = Field(max_length=64)


def user_out(u: models.User):
    return {"id": u.id, "name": u.name, "email": u.email, "mobile": u.mobile}


def make_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    return jwt.encode({"sub": str(user_id), "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer),
                     db: Session = Depends(get_db)) -> models.User:
    if creds is None:
        raise HTTPException(status_code=401, detail="Please log in to continue")
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Session expired. Please log in again")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Account not found. Please sign up again")
    return user


@router.post("/signup")
def signup(data: SignupIn, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == data.email).first():
        raise HTTPException(status_code=409, detail="This email is already registered. Please log in")
    hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
    user = models.User(name=data.name.strip(), email=data.email,
                       mobile=data.mobile, password_hash=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"token": make_token(user.id), "user": user_out(user)}


@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    ok = user and bcrypt.checkpw(data.password.encode(), user.password_hash.encode())
    if not ok:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"token": make_token(user.id), "user": user_out(user)}


@router.get("/me")
def me(user: models.User = Depends(get_current_user)):
    return user_out(user)