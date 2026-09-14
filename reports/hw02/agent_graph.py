
from typing import Any, Dict, TypedDict, Literal
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
from langgraph.graph import StateGraph,END

class AgentState(TypedDict):
    title:str
    content:str
    email:str
    strict:bool
    task:str
    llm:Any
    planner_proposal: Dict[str,Any]
    reviewer_feedback: Dict[str, Any]
    turn_count:int

llm = ChatOllama(model="qwen3:8b")

def planner_node(state:AgentState) -> Dict[str,Any]:
    print("--NODE: Planner ---")
    #planner logic
    prompt = (
        f"You are the planner agent. Generate 3 subject tags and a 25 max word summary of the blog content"
        "Return a JSON object output\n"
        "{ tags: three unique subject tags, summary: 25 max word summary of the blog}"
        "Rules:"
        "- do not copy and paste the blog content as use that as the summary"
        "- summary must be rephrased in your own words"
        "- output must be in JSON"
    )
    #call llm which is qwen3:8b from ollama
    result = llm.invoke(prompt)
    print("Response: ", result.content)
    try:
        #json output from the llm
        proposal=json.loads(result.content)
    except json.JSONDecodeError as e:
        print("JSON parsing error: ", e)
        proposal = {"tags": [], "summary":"", "error":str(e)}
    return {"planner_proposal": proposal}

def reviewer_node(state:AgentState) -> Dict[str,Any]:
    print("--NODE: Reviewer ---")
    #reviewer logic
    prompt = (
        f"You are the reviewer agent. Validate the tags and summary from the planner node"
        "\nOriginal Content:\n"
        f"Title: {state['title'],}, Content: {state['content']}\n"
        
        "\nPlanner proposal Content:\n"
        f"JSON content: {json.dumps(state['planner_proposal'])}"
        
        "Rules:"
        "- make sure there are only three tags"
        "- do not repeat the title, content, or proposal json content"
        "- make sure summary is not a copy paste from the content and the summary is a max 25 words. if any of that is false, then rewrite the summary to be a max 25 words"
        "- return only a valid JSON object only"
    )
    #call llm which is qwen3:8b from ollama
    result = llm.invoke(prompt)
    print("Feedback: ", result.content)
    try:
        #json output from the llm
        feedback=json.loads(result.content)
    except json.JSONDecodeError as e:
        print("JSON parsing error: ", e)
        feedback = {"tags": [], "summary":"", "error":str(e)}
        
    #correction loop testing so reviewer_node always return an issue
    #should see graph route the task back to planner
    # feedback["has_changes"] = True
    
    feedback["has_changes"]=(
        feedback.get("tags") != state["planner_proposal"].get("tags") or feedback.get("summary") != state["planner_proposal"].get("summary")
    )
    return {"reviewer_feedback": feedback}

def supervisor_node(state:AgentState) -> Dict[str,Any]:
    #to modify state like incrementing turn counter
    print("--NODE: Supervisor ---")
    tc=state.get("turn_count",0) +1
    print("Turn count:", tc)
    return {"turn_count":tc}

def router_logic(state:AgentState) -> Literal["planner", "reviewer", "end"]:
    #reads state and decide where to go next by return, a string 
    print("--Routing Logic---")
    #check if no planner proposal then go to planner
    if not state.get("planner_proposal") or state["planner_proposal"] == {}:
        print("Routing to planner because no planner proposal")
        return "planner"
    
    #check if no reviewer feedback then go to reviewer
    if not state.get("reviewer_feedback") or state["reviewer_feedback"] == {}:
        print("Routing to reviewer because no reviewer feedback")
        return "reviewer"
        
    #check if reviewer made changes and turn limit is not exceeded to loop back to planner
    #part 4 test turn ceilings 2 and 10, test 5 for part 3 to see what happens
    if state.get("reviewer_feedback", {}).get("has_changes") and state.get("turn_count",0) < 5:
        print(f"Routing to back planner because reviewer made changes and turn count is {state.get('turn_count',0)}, which is less than turn count limit 5")
        return "planner"
    
    print("Routing to end")
    return "end"
    
def main():
    #same as hw one blog content, title, and email
    #to wire everything together
    test={
        "title": "Slicon VS Plastic Toys",
        "content": "Many toys now lean away from plastic as silicon provides a fun new texture. Its flexible structure and softness are more appealing to parents as there are less risk of their child being hurt by these toys.",
        "email": "test@gmail.com",
        "strict": True,
        "task":"summarize",
        "llm":llm,
        "planner_proposal":{},
        "reviewer_feedback": {},
        "turn_count": 0
    }
    
    #make graph with normal workflow
    workflow_graph = StateGraph(AgentState)
    #add nodes for all agents
    workflow_graph.add_node("planner", planner_node)
    workflow_graph.add_node("reviewer", reviewer_node)
    workflow_graph.add_node("supervisor", supervisor_node)
    
    workflow_graph.set_entry_point("supervisor")
    workflow_graph.add_conditional_edges(
        "supervisor",
        router_logic,{
            "planner": "planner",
            "reviewer": "reviewer",
            "end": END
        }
    )
    #after planner and reviewer go to supervisor to keep track of turn count
    workflow_graph.add_edge("planner", "supervisor")
    workflow_graph.add_edge("reviewer", "supervisor")
    compile= workflow_graph.compile()
    
    #invoke graph with intial state aka test case blog stuff
    result = compile.invoke(test)
    print("\nResult")
    print("Turn count: ",result.get('turn_count',0))
    print("Planner tags ",result['planner_proposal'].get('tags', 'N/A'))
    print("Planner summary: ",result['planner_proposal'].get('summary', 'N/A'))
    print("Reviwer tags: ",result['reviewer_feedback'].get('tags', 'N/A'))
    print("Reviwer summary: ",result['reviewer_feedback'].get('summary', 'N/A'))
    print("Changes made: ",result['reviewer_feedback'].get('has_changes', False))

    #to see output from each step
    print("\n\nResult using .stream() method")
    stream = test.copy()
    stream["planner_proposal"]={}
    stream["reviewer_feedback"]={}
    stream["turn_count"]=0
    
    #.stream() method called to see output from each step
    for step in compile.stream(stream):
        print("Stream step output: ", step)
        print("\n")

if __name__ == "__main__":
    main()
    
    
    
    
    
    
