from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import OSINTRecord, ActivityType, ThematicVector

with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.commit()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="OSINT MVP API")


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


@app.get("/records/", response_model=list[OSINTRecordOut])
def list_records(db: Session = Depends(get_db)):
    return db.query(OSINTRecord).order_by(OSINTRecord.created_at.desc()).all()


@app.post("/records/", response_model=OSINTRecordOut)
def create_record(record: OSINTRecordCreate, db: Session = Depends(get_db)):
    db_record = OSINTRecord(**record.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record
