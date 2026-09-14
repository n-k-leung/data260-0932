# Run instructions for Homework 1

# Requirements
- Olama installation (https://ollama.com/download/windows)
- Python 3.11 or 3.12
    run the following commands:
    python –version 
    winget install Python.Python.3.12 #(run if you have python version that isnt 3.11 or 3.12)

# Clone Repository
git clone https://github.com/n-k-leung/data260-0932

# Running FastAPI
1. Change directory to be reports/hw02/'Open Source Package Vul Management'
2. Run the following command 

python main.py

# Stateful Agent Graph
1. Change directory to be reports/hw02/
2. Connect to ollama

ollama serve        
ollama pull qwen3:8b

3. Run the following command 

python agent_graph.py

# Output Schema and Loop Safety
1. Change directory to be reports/hw02/
2. Connect to ollama

ollama serve        
ollama pull qwen3:8b

3. Run the following command 

python part4.py

# Output Metrics
1. Change directory to be reports/hw02/
2. Run the following command 
python output_metrics.py

# Verifying files
1. Change directory to be reports/hw02/
2. Run the following command
python .\verify_hw02.py

