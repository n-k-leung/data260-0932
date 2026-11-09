# Run instructions for Homework 3

# Requirements
- Python 3.11 or 3.12
    run the following commands:
    python –version 
    winget install Python.Python.3.12 #(run if you have python version that isnt 3.11 or 3.12)

# Clone Repository
git clone https://github.com/n-k-leung/data260-0932

# Part 1
1. Change directory to be reports/hw09
2. Run the following commands
venv\Scripts\activate
pip install -r .\requirements.txt
docker compose up -d
python .\view_counter.py

# Part 2
1. Change directory to be reports/hw09
2. Run the following commands
One terminal:
venv\Scripts\activate
pip install -r .\requirements.txt
docker compose up -d
docker ps
docker logs kafka-init

One terminal:
ollama pull qwen3:8b

One terminal:
cd .\agents\
python .\planner.py

One terminal:
cd .\agents\
python .\writer.py

One terminal:
cd .\agents\
python .\reviewer.py

One terminal:
venv\Scripts\activate
python .\test_semantic_cache.py

# Part 3
1. Change directory to be reports/hw09
2. Run the following commands
One terminal:
venv\Scripts\activate
pip install -r .\requirements.txt
docker compose up -d
docker ps
docker logs kafka-init

One terminal:
ollama pull qwen3:8b

One terminal:
cd .\agents\
python .\planner.py

One terminal:
cd .\agents\
python .\writer.py

One terminal:
cd .\agents\
python .\reviewer.py

One terminal:
venv\Scripts\activate
python .\threshold_sweep.py
(stop agents and restart before running next file so its cleared)
python .\stale.py

# Part 4
1. Change directory to be reports/hw09/part4_self_improve_agent
python .\train.py
python .\validate.py
python .\evaluate_test.py

# Verifying files
1. Change directory to be reports/hw09/part4_self_improve_agent
2. Run the following command
python .\verify-hw09.py

