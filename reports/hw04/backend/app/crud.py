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



