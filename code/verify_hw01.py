import importlib.util,json,os,sys
from datetime import datetime, timezone
root=os.path.join(os.path.dirname(__file__), "..")
root=os.path.abspath(root)
sys.path.insert(0,os.path.join(root,"src"))
checks=[]

def check(name, ok,detail=""):
    checks.append({"check":name, "passed":bool(ok), "detail":detail})
    
def file_exists(path):
    return os.path.isfile(os.path.join(root,path))

check("AGENT.md exists at github repo", file_exists("AGENT.md"))
check("src/model_client.py exists at github repo", file_exists("src/model_client.py"))
check("code/hw1_client.py exists at github repo", file_exists("code/hw1_client.py"))
check("code/agents_demo.py exists at github repo", file_exists("code/agents_demo.py"))
check("code/web_application/index.html exists at github repo", file_exists("code/web_application/index.html"))
check("code/web_application/package_vulnerabilities.js exists at github repo", file_exists("code/web_application/package_vulnerabilities.js"))

agent_ok, agent_detail=False, "file missing"
if file_exists("AGENT.md"):
    text=open(os.path.join(root, "AGENT.md")).read().lower()
    agent_ok="bullet" in text
    agent_detail="mentions bullet point format" if agent_ok else "did not mention bullet point formatting" 
check("AGENT.md needs to say bullet point formating", agent_ok, agent_detail)

ollama_ok, ollama_detail = False, ""
try:
    import ollama
    client = ollama.Client(host=os.environ.get("OLLAMA_URL", "http://localhost:11434"))
    client.list()
    ollama_ok=True
    ollama_detail= "Ollama is open and can be connected to"
except Exception:
    ollama_detail="Ollama is not reachable, check if ollama is openeds"
check("Ollama server if connected or not", ollama_ok,ollama_detail)

requried= [c for c in checks if c["check"]!="Ollama is connected"]
all_pass = all(c["passed"] for c in requried)

result ={
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "overall_stat": "PASS" if all_pass else "FAIL",
    "checks": checks
}
output_path=os.path.join(root, "reports", "hw01", "verification.json")
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path,"w") as f:
    json.dump(result,f,indent=3)
print(json.dumps(result,indent=3))
print("done")
sys.exit(0 if all_pass else 1)