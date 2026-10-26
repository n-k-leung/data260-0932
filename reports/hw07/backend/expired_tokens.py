from app.security import create_access_token

print(create_access_token({"sub": "alice", "role": "reader"}, expires_minutes=-5))
