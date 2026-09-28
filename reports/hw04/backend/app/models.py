from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from .database import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash=Column(String(255), nullable=False)


class SessionToken(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True, index=True)  # session token
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
class Vul(Base):
    __tablename__ = "vulnerabilities"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    package_name = Column(String(255), nullable=False)
    severity = Column(String(255), nullable=False)
    advisories = relationship(
        "Advisory",
        primaryjoin="Vul. id == Advisory.vul_id",
        foreign_keys="Advisory.vul_id",
        viewonly=True,
    )

class Advisory (Base):
    __tablename__ = "advisories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vul_id = Column(Integer, nullable=False)
    fix_version = Column(String(50), nullable=False)