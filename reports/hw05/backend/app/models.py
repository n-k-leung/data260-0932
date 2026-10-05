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
        primaryjoin="Vul.id == Advisory.vul_id",
        foreign_keys="Advisory.vul_id",
        viewonly=True,
    )
    vul_code = Column(String(50), nullable=False, unique=True)
    report_count = Column(Integer, nullable=False, default=0)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    #which vendor this vul is for
    vendor = relationship("Vendor", back_populates="vulnerabilities")

class Advisory (Base):
    __tablename__ = "advisories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vul_id = Column(Integer, nullable=False)
    fix_version = Column(String(50), nullable=False)
    
class Vendor (Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(100), nullable=False)
    contact_email = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    #all vulnerabilities from specific vendor
    vulnerabilities = relationship("Vul", back_populates="vendor")