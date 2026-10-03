from sqlalchemy.orm import Session
from . import models, schema
from datetime import datetime, timedelta, timezone
import hashlib

def hash_password(password: str) -> str:
  return hashlib. sha256(password.encode()).hexdigest()

def create_user(db: Session, payload: schema.UserCreate):
  hashed = hash_password(payload.password)
  user = models.User(name=payload.name, email=payload.email, password_hash=hashed)
  db.add(user)
  db.commit()
  db.refresh(user)
  return user

def get_users(db: Session):
  return db.query(models.User).order_by(models.User.id.asc()).all()

def get_user(db: Session, user_id: int):
  return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
  return db. query(models.User).filter(models.User.email == email).first()


def update_user(db: Session, user_id: int, payload: schema.UserUpdate):
  user = get_user(db, user_id)
  if not user:
      return None
  user.name = payload.name
  user.email = payload.email
  db.commit()
  db.refresh(user)
  return user

def delete_user(db: Session, user_id: int):
  user = get_user(db, user_id)
  if not user:
      return None
  db.delete(user)
  db.commit()
  return user

#functions for vulnerabilites, follows ame locgic as useres demo
def create_vul(db: Session, payload: schema.VulCreate):
  vul = models.Vul(package_name=payload.package_name, severity=payload.severity)
  db.add(vul)
  db.commit()
  db.refresh(vul)
  return vul

def get_vuls(db: Session):
  return db.query(models.Vul).order_by(models.Vul.id.asc()).all()

def get_vul(db: Session, vul_id: int):
  return db.query(models.Vul).filter(models.Vul.id == vul_id).first()

def update_vul(db: Session, vul_id: int, payload: schema.VulUpdate):
  vul = get_vul(db, vul_id)
  if not vul:
      return None
  vul.package_name = payload.package_name
  vul.severity = payload.severity
  db.commit()
  db.refresh(vul)
  return vul

def delete_vul(db: Session, vul_id: int):
  vul = get_vul(db, vul_id)
  if not vul:
      return None
  db.delete(vul)
  db.commit()
  return vul

def create_vendor(db: Session, payload: schema.VendorCreate):
  vendor = models. Vendor(name=payload.name, industry=payload.industry, contact_email=payload.contact_email)
  db. add (vendor)
  db.commit()
  db.refresh(vendor)
  return vendor

def get_vendors(db: Session, skip: int = 0, limit: int = 50):
  return db. query(models.Vendor).order_by(models.Vendor.id.asc()).offset(skip).limit(limit).all()

def get_vendor(db: Session, vendor_id: int):
  return db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()

def update_vendor(db: Session, vendor_id: int, payload: schema.VendorUpdate):
  vendor = get_vendor(db, vendor_id)
  if not vendor:
    return None
  vendor .name = payload. name
  vendor.industry = payload.industry
  vendor .contact_email = payload.contact_email
  db.commit()
  db.refresh(vendor)
  return vendor

def delete_vendor(db: Session, vendor_id: int):
  vendor = get_vendor(db, vendor_id)
  if not vendor:
    return None
  # do not delete a vendor that still has vulnerabilities pointing to it
  has_children = db.query(models.Vul).filter(models.Vul.vendor_id == vendor_id).first()
  if has_children:
    raise ValueError("Vendor still has vulnerabilities, cannot delete")
  db.delete(vendor)
  db.commit()
  return vendor

def get_vuls_by_vendor(db: Session, vendor_id: int):
  return db. query(models.Vul). filter(models.Vul.vendor_id == vendor_id).all()

