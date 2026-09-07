from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import db_models, schemas
from app.services.security import create_access_token, password_hash
from app.services.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserRegister, db: Session = Depends(get_db), _: None = Depends(enforce_rate_limit)):
    email = payload.email.strip().lower()
    if db.query(db_models.User).filter(db_models.User.email == email).first():
        raise HTTPException(409, "Email is already registered")
    user = db_models.User(email=email, password_hash=password_hash.hash(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.TokenOut(access_token=create_access_token(user.id))


@router.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db), _: None = Depends(enforce_rate_limit)):
    user = db.query(db_models.User).filter(db_models.User.email == payload.email.strip().lower()).first()
    if not user or not password_hash.verify(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return schemas.TokenOut(access_token=create_access_token(user.id))