python -c "import secrets; print(secrets.token_hex(32))"
cd .\reports\hw07\backend
python .\seeding_users.py
venv\Scripts\activate                    
pip install -r .\requirements.txt 
uvicorn app.main:app --port 8032 --reload