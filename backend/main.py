from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, hash_password, log_audit, require_role, verify_password
from database import Base, engine, get_db
from models import ActivityType, OSINTRecord, RoleEnum, ThematicVector, User

with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.commit()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="OSINT MVP API")


class UserCreate(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    role: RoleEnum
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OSINTRecordCreate(BaseModel):
    source_url: Optional[str] = None
    content: str
    thematic_vector: ThematicVector
    activity_type: ActivityType
    jtf_assignment: str
    province: str
    sentiment_score: float = 0.0
    threat_score: float = 0.0


class OSINTRecordOut(BaseModel):
    id: int
    source_url: Optional[str]
    content: str
    thematic_vector: ThematicVector
    activity_type: ActivityType
    jtf_assignment: str
    province: str
    sentiment_score: float
    threat_score: float
    created_at: datetime

    class Config:
        from_attributes = True


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    is_first_user = db.query(User).count() == 0
    db_user = User(
        username=user.username,
        hashed_password=hash_password(user.password),
        role=RoleEnum.Admin if is_first_user else RoleEnum.Viewer,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    log_audit(db, db_user.username, "register", f"role={db_user.role.value}")
    return db_user


@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    log_audit(db, user.username, "login")
    return Token(access_token=create_access_token(user.username))


@app.get("/auth/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/records/", response_model=list[OSINTRecordOut])
def list_records(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(OSINTRecord).order_by(OSINTRecord.created_at.desc()).all()


@app.post("/records/", response_model=OSINTRecordOut)
def create_record(
    record: OSINTRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.Admin, RoleEnum.Analyst)),
):
    db_record = OSINTRecord(**record.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    log_audit(db, current_user.username, "create_record", f"record_id={db_record.id}")
    return db_record
