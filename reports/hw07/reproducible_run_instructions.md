# part 1
1. do the following instructions (one terminal):
python -c "import secrets; print(secrets.token_hex(32))"
cd .\reports\hw07\backend
python .\seeding_users.py
venv\Scripts\activate                    
pip install -r .\requirements.txt 
uvicorn app.main:app --port 8032 --reload
2. do the following instructions (another terminal):
cd .\reports\hw07\backend
npm run dev
3. on http://localhost:8032/docs test the functions and tokens by signing in and the roles what they can and cannot do
4. This can also be done on the front end

# part 2
1. do the following instructions:
ollama pull qwen3:8b
cd .\reports\hw07\mcp
python .\tasks.py
python .\reliability.py
python .\compare_reflection.py
2. You can look under raw/ for the reflexion runs

# part 3
1. do the following instructions
cd .\reports\hw07\mcp
python .\compare_reflection.py demo (to store, no model to test)
python .\compare_reflection.py (multiple runs)

# part 4
1. do the following instructions:
cd reports/hw07/part4
venv\Scripts\activate  
uvicorn servers:app --port 8032 
2. On the webiste put this url:https://lyftbikes.com/pricing and browse to select the 201802 csv file and 201803 csv files to run
3. You can look under raw/ for the json files and snapshots of pricing data with SHA-256 hash used for the run. It also has the scenarios where membership is better than pay per ride and visa versa

# part 5
1. do the following instructions:
cd reports/hw07/part4
python .\attack_p5.py

# part 6
1. do the following instructions:
cd reports/hw07/part6
python .\test.py