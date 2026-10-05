# Run instructions for Homework 3

# Requirements
- Python 3.11 or 3.12
    run the following commands:
    python –version 
    winget install Python.Python.3.12 #(run if you have python version that isnt 3.11 or 3.12)

# Clone Repository
git clone https://github.com/n-k-leung/data260-0932

# Part 1
1. Change directory to be reports/hw04/frontend
2. Run the following commands

npm install
npm run dev

You will be prompted to the: http://localhost:5173/
3. Change idrectory to be reports/hw04/backend
4. Run the following command
uvicorn app.main:app --reload --port 8032

5. Then open http://localhost:5173/ on your browser
6. Open Postman for a valid login
POST http://localhost:8032/auth/register
body:
{
  "name": "test",
  "email": "t@gmail.com",
  "password": "test"
}

7. On http://localhost:5173/ go to to login page and sign in with the test user
8. Go to the Vendors page and fill in the fields to add a Vendor. You should see the list of vendors below after adding it.

9. Go to the Add Vulnerability Record page and add vulnerability. The vendor_id should match to the vendor you just added

10. Go to the dashboard page and you should see the vulnerability record added.
11. Logout by clicking logout on the top right
12. Postman of each action tested using API endpoints. Do the following:

# Part 2
1. Change directory to be reports/hw05/mcp
2. Run the following commands
venv\Scripts\activate 
pip install -r requirements.txt
mcp dev meals.py #for TheMealDB mcp
mcp dev vul.py #for domain specific mcp
3. You will be prompted to mcp inspector. There, click the connect slider. After successful connection navigate to the Tool tab on the top.
4. On the tools tab, you should see the tools on the left of the screen.
5. For meals mcp:
test search_meals_by_name by clicking it and then fill in the fields like so and execute the tool:
    Query: Arrabiata
    Limit: 5
test meals_by_ingredient by clicking it and then fill in the fields like so and execute the tool:
    Ingredient: chicken
    Limit: 12
test random_meal by clicking it and execute the tool
test meals_details by clicking it and then fill in the fields like so and execute the tool:
    id: 52771
6. For vul mcp:
test search_vulnerabilities by clicking it and then fill in the fields like so and execute the tool:
    valid testing:
        package_name: nodejs
    error testing:
        package_name: #space
test get_vulnerability by clicking it and then fill in the fields like so and execute the tool:
    valid testing:
        vuln_id: 2
    error testing:
        vuln_id: 27
test count_by_severity by clicking it and then fill in the fields like so and execute the tool:
    valid testing:
        min_count: 0
    error testing:
        min_count: -1

# Part 3
1. Change directory to be reports/hw05/mcp
2. Run the following commands
venv\Scripts\activate 
pip install -r requirements.txt
python part3_testing.py

# Part 4
1. Change directory to be reports/hw05/mcp
2. Run the following commands
venv\Scripts\activate 
pip install -r requirements.txt
python test_part4.py

# Part 5
1. Change directory to be reports/hw05/mcp
2. Run the following commands
ollama serve
ollama pull qwen3:8b
"$env:PYTHONPATH="..\backend""
python part5.py

# Verifying files
1. Change directory to be reports/hw05/
2. Run the following command
python .\verify-hw05.py

