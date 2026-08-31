# Run instructions for Homework 1

# Requirements
- Docker installation (https://docs.docker.com/desktop/setup/install/windows-install/)
- Olama installation (https://ollama.com/download/windows)
- Python 3.11 or 3.12
    run the following commands:
    python –version 
    winget install Python.Python.3.12 #(run if you have python version that isnt 3.11 or 3.12)

# Clone Repository
git clone https://github.com/n-k-leung/data260-0932

## Running Vulnerability Form on Docker
1. Open Docker
2. Change directory to be code
3. Run the following commands to build and run the docker image

docker build -t my-web-app .    
docker run -d -p 8032:80 --name my-web-app-container my-web-app

4. On docker you should see my-web-app and clicking on the link directs you to (http://localhost:8032). You may manually type this into your browser.

5. To view the console on this site, you can click F12 and click the Console tab. This updates when you submit to the form.

## AWS ECS

## Agentic AI
1. Change directory to be code
2. Connect to ollama
ollama serve        
ollama pull qwen3:8b
3. Run the following command 
python .\agents_demo.py --title "Slicon VS Plastic Toys" --content "Many toys now lean away from plastic as silicon provides a fun new texture. Its flexible structure and softness are more appealing to parents as there are less risk of their child being hurt by these toys." --email "test@sjsu.edu" --strict

## Measuring Non-Determinism
1. Change directory to be code
2. Run the following command
python run nondeterminism.py

## Model Client and Token Accounting
1. Change directory to be code
2. Connect to ollama
ollama serve        
ollama pull qwen3:8b
3. Run the following command
python .\hw1_client.py
// example code to try is def divide(a,b):   if b=0:         x=0     else:           x=a/b
// note: paste code as one line
4. When prompted for input, to replicate my 5 step run with checking the stats run the following one at a time:
def divide(a,b):   if b=0:         x=0
else:              x=a/b
def divide(a,b):   if b==0:                x=0
/stats
def divide(a,b):   if b==0:                x=0 else:              x=a/b
def divide(a,b):   if b==0:                x=0 return x else:              x=a/b return x
/stats
/exit

## Verifying all files
1. Change directory to be code
2. Run the following command
python .\verify_hw01.py

