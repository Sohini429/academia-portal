"""Registration, login, token refresh and identity lookup."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import College, Company, Student, User
from ..responses import ok
from ..schemas import LoginRequest, RefreshRequest, RegisterRequest, UserOut
from ..security import (
    create_token_pair,
    current_user,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    user = User(email=email, password_hash=hash_password(payload.password), role=payload.role)
    db.add(user)
    db.flush()  # assign user.id before building the role profile

    if payload.role == "student":
        db.add(
            Student(
                user_id=user.id,
                name=payload.name,
                college_name=payload.college_name,
                branch=payload.branch,
                graduation_year=payload.graduation_year,
                cgpa=payload.cgpa,
            )
        )
    elif payload.role == "college":
        db.add(College(user_id=user.id, name=payload.name, city=payload.city))
    else:
        db.add(Company(user_id=user.id, name=payload.name, industry=payload.industry))

    db.commit()
    db.refresh(user)
    return ok({"user": UserOut.model_validate(user), **create_token_pair(user)})


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    # Same message for unknown email and wrong password - no account enumeration.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is deactivated")
    return ok({"user": UserOut.model_validate(user), **create_token_pair(user)})


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    claims = decode_token(payload.refresh_token, "refresh")
    user = db.get(User, int(claims["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer active")
    return ok(create_token_pair(user))


@router.get("/me")
def me(user: User = Depends(current_user)):
    profile = user.student or user.college or user.company
    return ok(
        {
            "user": UserOut.model_validate(user),
            "profile_name": getattr(profile, "name", None),
        }
    )
