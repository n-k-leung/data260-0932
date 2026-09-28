# Run instructions for Homework 3

# Requirements
- Python 3.11 or 3.12
    run the following commands:
    python –version 
    winget install Python.Python.3.12 #(run if you have python version that isnt 3.11 or 3.12)

# Clone Repository
git clone https://github.com/n-k-leung/data260-0932

# React Client
1. Change directory to be reports/hw04/frontend
2. Run the following commands

npm install
npm run dev

You will be prompted to the: http://localhost:5173/
3. Change idrectory to be reports/hw04/backend
4. Run the following command
uvicorn app.main:app --reload --port 8032

5. Then open http://localhost:5173/ on your browser

6. The login credentials to test are: email = t@gmail.com and password= test
7. Test to go from home page to login page by clicking login button
8. Test to login to home by clicking back to home button
9. Test to login with valid credentials and click the login on login page
10. Test home page by seeing if home  page is redirected after successful login
11. Test logout by clicking logout button on home  page, this should redirect you to the login page
12. Test idle time out by loging in successfully and waiting 30 mins and then refreshing should redirect you to login page
13. Test invalid login message, by testing invalid credentials: email = test and password= test
14. Test going to home page by going to http://localhost:5173/home when you aren't logged in, you should still be on login page 

# MySQL Persistence and Server-Side Sessions
1. Open Postman and do the following:

POST http://localhost:8032/auth/register

POST http://localhost:8032/auth/login

POST http://localhost:8032/vuls

GET http://localhost:8032/vuls/3

PUT http://localhost:8032/vuls/2

DEL http://localhost:8032/vuls/2

# N+1 Measurement and Query Tuning
1. Change directory to be reports/hw04/backend
2. Run the following command
python seed.py
python measure.py
python explain_index.py
3. Open Postman and do the following:

GET http://localhost:8032/vuls/naive?limit=50

GET http://localhost:8032/vuls/naive?limit=200

GET http://localhost:8032/vuls/fixed?limit=200

GET http://localhost:8032/vuls/fixed?limit=50

GET http://localhost:8032/vuls/fixed?limit=10

GET http://localhost:8032/vuls/naive?limit=10


# Build a Grounded RAG Question-Answering System
1. Change directory to be reports/hw04
2. Run the following command
python rag.py


# Verifying files
1. Change directory to be reports/hw04/
2. Run the following command
python .\verify-hw04.py

