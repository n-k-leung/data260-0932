from app import crud
from app.database import Base, SessionLocal, engine

# creates the new users table if missing

Base.metadata.create_all(bind=engine)

users_to_add = [
    ("alice", "alice123", "reader"),
    ("bob", "bob123", "writer"),
    ("carol", "carol123", "moderator"),
]
db = SessionLocal()
for username, password, role in users_to_add:
    if crud.get_user_by_username(db, username):
        print("already exists:", username)
        continue
    crud.create_user(db, username, password, role)
    print("created:", username, "->", role)
db.close()
