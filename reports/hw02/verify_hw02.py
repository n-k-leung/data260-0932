import concurrent.features
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import requests
import time
from langgraph.graph import StateGraph, END

try:
    import part4 as p
    ImportError=None
except Exception as e:
    p = None
    ImportError=str(e)

sys.path.insert(0,str(Path(__file__).resolve().parent))

SID4="0932"
PORT_BASE=8032
PREFIX="s0932"
SEED=932
VERIFY_SEED=260932
DOMAIN_ID=4
MODEL_CONFIG="qwen8:3b"

def get_commit_hash()->str:
    try:
        result=subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parent, capture_output=True,text=True,timeout=5
        )
        if result.returncode==0:
            return result.stdout.strip()
    except Exception:
        pass
    return "github repo is unavailable"

def check_fastapi()-> dict:
    url=f"http://localhost:{PORT_BASE}/api/packages"
    try:
        response=requests.get(url,timeout=5)
        if response.status_code==200:
            passed=True
        else:
            passed=False
        return{
            "name": "fastapi_responds",
            "detail": f"{url} worked, status: {response.status_code}",
            "passed": passed,
        }
    except Exception as e:
        return{
            "name": "fastapi_responds",
            "detail": f"{url} failed, {e}, fastapi is not running on PORT_BASE {PORT_BASE}",
            "passed": False,
        }
    
def smoke_graph():
    test={
        "title": "Slicon VS Plastic Toys",
        "content": "Many toys now lean away from plastic as silicon provides a fun new texture. Its flexible structure and softness are more appealing to parents as there are less risk of their child being hurt by these toys.",
        "email": "test@gmail.com",
        "strict": True,
        "task":"summarize",
        "llm":re.llm,
        "planner_proposal":{},
        "reviewer_feedback": {},
        "turn_count": 0,
        "turn_ceiling": 5,
        "attempts":0
    }
    
    #make graph with normal workflow
    workflow_graph = StateGraph(p.AgentState)
    #add nodes for all agents
    workflow_graph.add_node("planner", p.planner_node)
    workflow_graph.add_node("reviewer", p.reviewer_node)
    workflow_graph.add_node("supervisor", p.supervisor_node)

    workflow_graph.set_entry_point("supervisor")
    workflow_graph.add_conditional_edges(
        "supervisor",
        p.router_logic,{
            "planner": "planner",
            "reviewer": "reviewer",
            "end": END
        }
    )
    #after planner and reviewer go to supervisor to keep track of turn count
    workflow_graph.add_edge("planner", "supervisor")
    workflow_graph.add_edge("reviewer", "supervisor")
    compile= workflow_graph.compile()
    start=time.perf_counter()
    final_state= compile.invoke(test)
    elapsed_ms=(time.perf_counter()-start)*1000
    return final_state,elapsed_ms

def langgraph()->dict:
    if p is None:
        return{
            "name": "langgraph_works_and_returns_three_tags",
            "detail": f"failed to import agent_graph {ImportError}",
            "passed": False,
        }
    try:
        with concurrent.features.ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(smoke_graph)
            final_state, elapsed_ms=future.result(timeout=90)
    except concurrent.features.TimeoutError:
        return{
            "name": "langgraph_works_and_returns_three_tags",
            "detail": f"graph.invoke did not return within 90 seconds",
            "passed": False,
        }
    except Exception as e:
        return{
            "name": "langgraph_works_and_returns_three_tags",
            "detail": f"graph raised exception {e}",
            "passed": False,
        }
    proposal = final_state.get("planner_proposal", {})
    tags=proposal.get("tags", [])
    passed=len(tags)==3
    return{
        "name": "langgraph_works_and_returns_three_tags",
        "detail": f"finished time: {elapsed_ms}ms, attempts: {final_state.get('attempts')}, number of tags: {len(tags)}",
        "passed": passed,
    }

def main()-> None:
    checks = [check_fastapi(), langgraph()]
    passed_all = all(c["passed"] for c in checks)
    result={
        "sid4":SID4,
        "port_base":PORT_BASE,
        "prefix":PREFIX,
        "seed":SEED,
        "verify_seed":VERIFY_SEED,
        "domain_id":DOMAIN_ID,
        "commit_hash":get_commit_hash,
        "model_config":MODEL_CONFIG,
        "timestamp":datetime.now().isoformat(timespec="seconds"),
        "checks":checks,
        "passed_all":passed_all,
    }
    
    output=Path(__file__).resolve().parent/"verification.json"
    output.write_text(json.dumps(result))
    
    print(json.dumps(result))
    print("ouput written to: ",output)
    sys.exit(0 if passed_all else 1)
    
if __name__ == "__main__":
    main()
            
