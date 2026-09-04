import enum
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import literal_column, text
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, hash_password, log_audit, require_role, verify_password
from database import Base, SessionLocal, engine, get_db
from embeddings import embed, to_pgvector_literal
from models import (
    ActivityType, Alert, AlertSeverity, Keyword, KeywordCategory,
    MonitoredSource, OSINTRecord, RoleEnum, ThematicVector, User,
)
from scan import evaluate_record, run_scan


class SourcePlatform(str, enum.Enum):
    X_Twitter = "X/Twitter"
    Telegram = "Telegram"
    Facebook = "Facebook"
    Field_Report = "Field Report"


with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.commit()

Base.metadata.create_all(bind=engine)

# Patch columns added after initial deploy onto pre-existing tables (create_all only creates missing tables).
with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE osint_records ADD COLUMN IF NOT EXISTS source_platform VARCHAR(50) NOT NULL DEFAULT 'Field Report'"
    ))
    conn.commit()

app = FastAPI(title="OSINT MVP API")


def _scheduled_scan():
    db = SessionLocal()
    try:
        run_scan(db)
    finally:
        db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(_scheduled_scan, "interval", hours=1, id="hourly_scan")
scheduler.start()


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
    source_platform: SourcePlatform = SourcePlatform.Field_Report


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
    source_platform: SourcePlatform
    created_at: datetime

    class Config:
        from_attributes = True


class OSINTRecordSearchOut(OSINTRecordOut):
    similarity: float = 0.0


class OSINTRecordUpdate(BaseModel):
    source_url: Optional[str] = None
    content: Optional[str] = None
    thematic_vector: Optional[ThematicVector] = None
    activity_type: Optional[ActivityType] = None
    source_platform: Optional[SourcePlatform] = None
    jtf_assignment: Optional[str] = None
    province: Optional[str] = None
    sentiment_score: Optional[float] = None
    threat_score: Optional[float] = None


class KeywordCreate(BaseModel):
    term: str
    category: KeywordCategory


class KeywordOut(BaseModel):
    id: int
    term: str
    category: KeywordCategory
    created_at: datetime

    class Config:
        from_attributes = True


class SourceStatus(str, enum.Enum):
    Active = "Active"
    Pending = "Pending"
    Paused = "Paused"


class SourceStatusUpdate(BaseModel):
    status: SourceStatus


class MonitoredSourceCreate(BaseModel):
    platform: SourcePlatform
    handle: str
    status: SourceStatus = SourceStatus.Pending
    notes: Optional[str] = None


class MonitoredSourceOut(BaseModel):
    id: int
    platform: SourcePlatform
    handle: str
    status: SourceStatus
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    id: int
    record_id: Optional[int]
    rule_type: str
    severity: AlertSeverity
    message: str
    acknowledged: bool
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


@app.get("/records/search", response_model=list[OSINTRecordSearchOut])
def search_records(
    q: str,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query_vector = to_pgvector_literal(embed(q))
    # query_vector is generated internally from floats (never raw user text), so inlining is safe.
    distance_expr = literal_column(f"(embedding <=> '{query_vector}'::vector)")

    rows = (
        db.query(OSINTRecord, distance_expr.label("distance"))
        .filter(OSINTRecord.embedding.isnot(None))
        .order_by(distance_expr)
        .limit(limit)
        .all()
    )

    results = []
    for record, distance in rows:
        item = OSINTRecordSearchOut.model_validate(record)
        item.similarity = 1 - distance
        results.append(item)
    return results


@app.post("/records/", response_model=OSINTRecordOut)
def create_record(
    record: OSINTRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.Admin, RoleEnum.Analyst)),
):
    db_record = OSINTRecord(**record.model_dump())
    db_record.embedding = embed(record.content)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    log_audit(db, current_user.username, "create_record", f"record_id={db_record.id}")
    evaluate_record(db, db_record)
    return db_record


@app.patch("/records/{record_id}", response_model=OSINTRecordOut)
def update_record(
    record_id: int,
    update: OSINTRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.Admin, RoleEnum.Analyst)),
):
    db_record = db.query(OSINTRecord).filter(OSINTRecord.id == record_id).first()
    if not db_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    changes = update.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(db_record, field, value)
    if "content" in changes:
        db_record.embedding = embed(db_record.content)

    db.commit()
    db.refresh(db_record)
    log_audit(db, current_user.username, "update_record", f"record_id={record_id} fields={list(changes.keys())}")
    return db_record


@app.delete("/records/{record_id}")
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.Admin)),
):
    db_record = db.query(OSINTRecord).filter(OSINTRecord.id == record_id).first()
    if not db_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    db.query(Alert).filter(Alert.record_id == record_id).delete()
    db.delete(db_record)
    db.commit()
    log_audit(db, current_user.username, "delete_record", f"record_id={record_id}")
    return {"ok": True}


@app.get("/keywords/", response_model=list[KeywordOut])
def list_keywords(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Keyword).order_by(Keyword.term).all()


@app.post("/keywords/", response_model=KeywordOut)
def create_keyword(
    keyword: KeywordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.Admin, RoleEnum.Analyst)),
):
    if db.query(Keyword).filter(Keyword.term == keyword.term).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Keyword already exists")
    db_keyword = Keyword(**keyword.model_dump())
    db.add(db_keyword)
    db.commit()
    db.refresh(db_keyword)
    log_audit(db, current_user.username, "create_keyword", f"term={db_keyword.term}")
    return db_keyword


@app.delete("/keywords/{keyword_id}")
def delete_keyword(
    keyword_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.Admin)),
):
    db_keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not db_keyword:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")
    db.delete(db_keyword)
    db.commit()
    log_audit(db, current_user.username, "delete_keyword", f"term={db_keyword.term}")
    return {"ok": True}


@app.get("/alerts/", response_model=list[AlertOut])
def list_alerts(
    unacknowledged_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Alert)
    if unacknowledged_only:
        query = query.filter(Alert.acknowledged.is_(False))
    return query.order_by(Alert.created_at.desc()).all()


@app.post("/alerts/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.Admin, RoleEnum.Analyst)),
):
    db_alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    db_alert.acknowledged = True
    db.commit()
    db.refresh(db_alert)
    return db_alert


@app.post("/scan/run")
def trigger_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.Admin, RoleEnum.Analyst)),
):
    new_alerts = run_scan(db)
    log_audit(db, current_user.username, "manual_scan", f"new_alerts={new_alerts}")
    return {"new_alerts": new_alerts}


@app.get("/sources/", response_model=list[MonitoredSourceOut])
def list_sources(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(MonitoredSource).order_by(MonitoredSource.platform, MonitoredSource.handle).all()


@app.post("/sources/", response_model=MonitoredSourceOut)
def create_source(
    source: MonitoredSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.Admin, RoleEnum.Analyst)),
):
    db_source = MonitoredSource(**source.model_dump())
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    log_audit(db, current_user.username, "create_source", f"handle={db_source.handle}")
    return db_source


@app.patch("/sources/{source_id}", response_model=MonitoredSourceOut)
def update_source_status(
    source_id: int,
    status_update: SourceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.Admin, RoleEnum.Analyst)),
):
    db_source = db.query(MonitoredSource).filter(MonitoredSource.id == source_id).first()
    if not db_source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    db_source.status = status_update.status.value
    db.commit()
    db.refresh(db_source)
    return db_source


@app.delete("/sources/{source_id}")
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RoleEnum.Admin)),
):
    db_source = db.query(MonitoredSource).filter(MonitoredSource.id == source_id).first()
    if not db_source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    db.delete(db_source)
    db.commit()
    log_audit(db, current_user.username, "delete_source", f"handle={db_source.handle}")
    return {"ok": True}
