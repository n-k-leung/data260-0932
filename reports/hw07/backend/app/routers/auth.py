from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import crud, schema
from ..database import get_db
from ..dependson import get_current_user
from ..security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=schema.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):

    # fetch the user from db and verifying the password hash
    user = crud.get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # creating token after valid credentials
    token = create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=schema.UserMe)
def me(current_user=Depends(get_current_user)):
    # depends on current user and authenticating that
    return current_user


# old file for history mentioned
# from fastapi import APIRouter, Depends, HTTPException, Request, Response
# from sqlalchemy.orm import Session
# from sqlalchemy.exc import IntegrityError
# from datetime import datetime, timedelta

# from .. database import get_db
# from .. import crud, schema
# from .. session_crud import create_session, get_session, delete_session,
# SESSION_TTL_MINUTES

# router = APIRouter(prefix="/auth")
# def require_session(request: Request, db: Session = Depends(get_db)):
#   token = request.cookies.get("session_id")
#   if not token:
#     raise HTTPException(status_code=401, detail="Not logged in")

#   s = get_session(db, token)
#   if not s:
#     raise HTTPException(status_code=401, detail="Session expired or invalid")

#   s.expires_at = datetime.utcnow() + timedelta(minutes=SESSION_TTL_MINUTES)
#   db.commit()
#   return s

# @router.post("/register", response_model=schema.UserOut)
# def register(payload: schema.UserCreate, db: Session = Depends(get_db)):
#   try:
#     return crud.create_user(db, payload)
#   except IntegrityError:
#     db.rollback()
#     raise HTTPException(status_code=409, detail="Email already exists")

# #check the hashed password, save session row in the sessions table, and send cookie
# @router.post("/login")
# def login(payload: schema.LoginRequest, response: Response, db: Session =
# Depends(get_db)):
#   user = crud.get_user_by_email(db, payload.email)

#   if not user or user.password_hash != crud.hash_password(payload.password):
#     raise HTTPException(status_code=401, detail="Invalid user or password")

#   s = create_session(db, user_id=user.id)
#   response.set_cookie(
#   key="session_id",
#   value=s.id,
#   httponly=True,
#   samesite="lax",
#   max_age=SESSION_TTL_MINUTES * 60 )
#   return {"message": "logged in", "user_id": user.id}

# @router.get("/me")
# def me(_session = Depends(require_session)):
#   return {"logged_in": True, "user_id": _session.user_id}

# #delete the session row and clear the cookie
# @router.post("/logout")
# def logout(request: Request, response: Response, db: Session = Depends(get_db)):
#   token = request.cookies.get("session_id")
#   if token:
#     delete_session(db, token)
#   response.delete_cookie("session_id")
#   return {"message": "logged out"}
