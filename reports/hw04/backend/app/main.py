from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import Response, Request
from .session_crud import create_session, get_session, delete_session

from .database import Base, engine, get_db, query_count
from . import crud, schema, models
from .routers.auth import router as auth_router, require_session
from sqlalchemy.orm import joinedload

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Open Source Vulnerability Management API")

# Allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/users", response_model=schema.UserOut)
def add_user(payload: schema.UserCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_user(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")

@app.get("/users", response_model=list[schema.UserOut])
def list_users(
    db: Session = Depends(get_db),
    _session = Depends(require_session)
):
    return crud.get_users(db)

@app.get("/users/{user_id}", response_model=schema.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/users/{user_id}", response_model=schema.UserOut)
def edit_user(user_id: int, payload: schema.UserUpdate, db: Session = Depends(get_db)):
    try:
        user= crud.update_user(db, user_id, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email exists")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.delete("/users/{user_id}", response_model=schema.UserOut)
def remove_user(user_id: int, db: Session = Depends(get_db)):
    user = crud.delete_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

#vulnerabilities

@app.post("/vuls", response_model=schema.VulOut)
def add_vul(payload: schema.VulCreate, db: Session = Depends(get_db), _session = Depends(require_session)):

    return crud.create_vul(db, payload)
    
@app.get("/vuls", response_model=list[schema.VulOut])
def list_vuls(
    db: Session = Depends(get_db),
    _session = Depends(require_session)
):
    return crud.get_vuls(db)

@app.get("/vuls/naive", response_model=list[schema.VulAdvi])
def list_naive(response: Response, limit: int = 10, db: Session = Depends(get_db), _session = Depends(require_session)):
    query_count["n"] =0 
    vulns = db.query(models.Vul).order_by(models.Vul.id).limit(limit).all()
    result = []
    for v in vulns:
    # the extra query, run once per record
        advs = db.query(models.Advisory).filter(models.Advisory.vul_id == v.id).all()
        result.append({"id": v.id, "package_name": v.package_name, "severity": v.severity, "advisories": advs})
    response.headers["X-SQL-Count"] = str(query_count["n"])
    return result

@app.get("/vuls/fixed", response_model=list[schema.VulAdvi])
def list_fixed(response: Response, limit: int = 10, db: Session = Depends(get_db), _session = Depends(require_session)):
    query_count["n"]=0
    vulns = (db.query(models.Vul)
        .options(joinedload(models.Vul.advisories))
        .order_by(models.Vul.id).limit(limit).all())
    result = []
    for v in vulns:
        result.append({"id": v.id, "package_name": v.package_name, "severity": v.severity, "advisories": v.advisories})
    response.headers["X-SQL-Count"] = str(query_count["n"])
    return result

@app.get("/vuls/{vul_id}", response_model=schema.VulOut)
def get_vul(vul_id: int, db: Session = Depends(get_db), _session = Depends(require_session)):
    vul = crud.get_vul(db, vul_id)
    if not vul:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return vul

@app.put("/vuls/{vul_id}", response_model=schema.VulOut)
def edit_vul(vul_id: int, payload: schema.VulUpdate, db: Session = Depends(get_db), _session = Depends(require_session)):
    vul = crud.update_vul(db, vul_id, payload)
    if not vul:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return vul

@app.delete("/vuls/{vul_id}", response_model=schema.VulOut)
def remove_vul(vul_id: int, db: Session = Depends(get_db), _session = Depends(require_session)):
    vul = crud.delete_vul(db, vul_id)
    if not vul:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return vul



# implemented in routers file like in hw3
# @app.get("/auth/me")
# def me(_session = Depends(require_session)):
#     return {"logged_in": True, "user_id": _session.user_id}

# @app.post("/auth/login")
# def login(user_id: int, response: Response, db: Session = Depends(get_db)):
#     # Demo-simple: login using an existing user_id (no password)
#     user = crud.get_user(db, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")

#     s = create_session(db, user_id=user_id)

#     # cookie sent to browser/postman
#     response.set_cookie(
#         key="session_id",
#         value=s.id,
#         httponly=True,
#         samesite="lax",
#         max_age=30 * 60
#     )
#     return {"message": "logged in", "user_id": user_id}

# @app.post("/auth/logout")
# def logout(request: Request, response: Response, db: Session = Depends(get_db)):
#     token = request.cookies.get("session_id")
#     if token:
#         delete_session(db, token)
#     response.delete_cookie("session_id")
#     return {"message": "logged out"}