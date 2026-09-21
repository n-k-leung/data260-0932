# Run instructions for Homework 3

# Requirements
- Python 3.11 or 3.12
    run the following commands:
    python –version 
    winget install Python.Python.3.12 #(run if you have python version that isnt 3.11 or 3.12)

# Clone Repository
git clone https://github.com/n-k-leung/data260-0932

# Running FastAPI
1. Change directory to be reports/hw03
2. Run the following command 

python main.py

You will be prompted to the fastapi app: https://127.0.0.1:8032
3. The login credentials to test are: username = admin and password= password
4. Test to go from home page to login page by clicking login button
5. Test to login to home by clicking back to home button
6. Test to login with valid credentials and click the login on login page
7. Test dashboard by seeing if dashboard page is redirected after successful login
8. Test logout by clicking logout button on dashboard page, this should redirect you to the login page
9. Test idle time out by loging in successfully and waiting 60 seconds and then refreshing should redirect you to login page
10. Test invalid login message, by testing invalid credentials: username = test and password= test
11. Test going to dashboard by going to https://127.0.0.1:8032/dashboard when you aren't logged in, you should still be on login page 


# Compare Three LlamaIndex Chunking Techniques (Retrieval-Only RAG)
1. Change directory to be reports/hw03/
2. Installations: (run the following commands)
 pip install llama_index
 pip install llama-index-embeddings-huggingface
 pip install sentence_transformers
 pip install faiss-cpu
 pip install numpy
 pip install pandas
3. Run the following command to get the dataset of open source package vulnerabilities
python get_packages.py
4. Run the following command to do the one retrieval only pipeline per technique
python retrieval_pipeline.py
5. Run the following command to print metrics to a table
python metrics.py

# Verifying files
1. Change directory to be reports/hw03/
2. Run the following command
python .\verify-hw03.py

