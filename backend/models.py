from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import enum
from database import Base

class RoleEnum(str, enum.Enum):
    Admin = "Admin"
    Analyst = "Analyst"
    Viewer = "Viewer"

class ActivityType(str, enum.Enum):
    Violent = "Violent"
    Non_Violent = "Non-Violent"

class ThematicVector(str, enum.Enum):
    Electoral_Security = "Electoral Security"
    Securitization = "Securitization & Threat Groups"
    Territorial_Maritime = "Territorial & Maritime Security"

class KeywordCategory(str, enum.Enum):
    Threat_Group = "Threat Group"
    Election = "Election"
    Region = "Region"

class AlertSeverity(str, enum.Enum):
    High = "High"
    Medium = "Medium"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.Viewer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    action = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class OSINTRecord(Base):
    __tablename__ = "osint_records"

    id = Column(Integer, primary_key=True, index=True)
    source_url = Column(String(508), nullable=True)
    content = Column(Text, nullable=False)
    thematic_vector = Column(SQLEnum(ThematicVector), nullable=False)
    activity_type = Column(SQLEnum(ActivityType), nullable=False)
    jtf_assignment = Column(String(100), nullable=False)  # e.g., JTF ZAMPELAN, JTF ORION
    province = Column(String(100), nullable=False)        # e.g., Sulu, Zamboanga del Sur
    sentiment_score = Column(Float, default=0.0)
    threat_score = Column(Float, default=0.0)
    embedding = Column(Vector(384))  # For semantic search / pgvector
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    term = Column(String(100), unique=True, nullable=False)
    category = Column(SQLEnum(KeywordCategory), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("osint_records.id"), nullable=True)
    rule_type = Column(String(50), nullable=False)  # high_threat | velocity | keyword_match
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    message = Column(Text, nullable=False)
    acknowledged = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
