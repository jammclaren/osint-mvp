from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Alert, AlertSeverity, Keyword, OSINTRecord

HIGH_THREAT_THRESHOLD = 7.0
VELOCITY_WINDOW = timedelta(hours=1)
VELOCITY_THRESHOLD = 3


def _already_alerted(db: Session, rule_type: str, record_id: int | None = None) -> bool:
    query = db.query(Alert).filter(Alert.rule_type == rule_type)
    if record_id is not None:
        query = query.filter(Alert.record_id == record_id)
    return query.first() is not None


def _check_high_threat(db: Session, record: OSINTRecord) -> None:
    if record.threat_score < HIGH_THREAT_THRESHOLD:
        return
    if _already_alerted(db, "high_threat", record.id):
        return
    db.add(Alert(
        record_id=record.id,
        rule_type="high_threat",
        severity=AlertSeverity.High,
        message=f"High threat score ({record.threat_score}) in {record.province}: {record.content[:120]}",
    ))


def _check_keyword_match(db: Session, record: OSINTRecord) -> None:
    keywords = db.query(Keyword).all()
    content_lower = record.content.lower()
    for kw in keywords:
        if kw.term.lower() not in content_lower:
            continue
        already = (
            db.query(Alert)
            .filter(Alert.rule_type == "keyword_match", Alert.record_id == record.id, Alert.message.contains(kw.term))
            .first()
        )
        if already:
            continue
        db.add(Alert(
            record_id=record.id,
            rule_type="keyword_match",
            severity=AlertSeverity.Medium,
            message=f"Keyword '{kw.term}' ({kw.category.value}) matched in {record.province}: {record.content[:120]}",
        ))


def _check_velocity(db: Session) -> None:
    since = datetime.now(timezone.utc) - VELOCITY_WINDOW
    counts = (
        db.query(OSINTRecord.thematic_vector, func.count(OSINTRecord.id))
        .filter(OSINTRecord.created_at >= since)
        .group_by(OSINTRecord.thematic_vector)
        .all()
    )
    for vector, count in counts:
        if count < VELOCITY_THRESHOLD:
            continue
        recent_duplicate = (
            db.query(Alert)
            .filter(Alert.rule_type == "velocity", Alert.created_at >= since, Alert.message.contains(vector.value))
            .first()
        )
        if recent_duplicate:
            continue
        db.add(Alert(
            record_id=None,
            rule_type="velocity",
            severity=AlertSeverity.High,
            message=f"Velocity spike: {count} records tagged '{vector.value}' in the last hour",
        ))


def evaluate_record(db: Session, record: OSINTRecord) -> None:
    _check_high_threat(db, record)
    _check_keyword_match(db, record)
    db.commit()


def run_scan(db: Session) -> int:
    before = db.query(Alert).count()
    for record in db.query(OSINTRecord).all():
        _check_high_threat(db, record)
        _check_keyword_match(db, record)
    _check_velocity(db)
    db.commit()
    after = db.query(Alert).count()
    return after - before
