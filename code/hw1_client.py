import argparse,json,os,sys

# have to do this so it gets the model_client.py bc located in differnt location
sys.path.insert(0,os.path.join(os.path.dirname(__file__),"..","src"))
from model_client import ModelClient
def load():
    agent=os.path.join(os.path.dirname(__file__),"..","AGENT.md")
    with open(agent)as f:
        return f.read()
def stats(num_turns, total_in_tok, total_out_tok,messages):
    l = len(json.dumps(messages))
    print(f"\n[/stats] turns={num_turns} total_input_tokens={total_in_tok} total_output_tokens={total_out_tok} chars={l}\n")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",default=os.environ.get("SMOL_MODEL", "qwen3:8b"))
    ap.add_argument("--base_url",default=os.environ.get("OLLAMA_URL", "http://localhost:11434"))
    args=ap.parse_args()
    
    client=ModelClient(model=args.model, base_url=args.base_url)
    messages=[{"role":"system", "content":load()}]
    
    num_turns=0
    total_in_toks=0
    total_out_toks=0
    
    print("Type code to review, /stats for stats, or /exit to stop the program")
    while True:
        try:
            user_input=input("you> ").strip()
        except EOFError:
            print("\n No input -- break")
            break
        if not user_input:
            continue
        if user_input=="/exit":
            print(f"\nEnding stats: turns={num_turns} | total_in_tokens={total_in_toks} | total_out_tokens={total_out_toks}")
            break
        if user_input=="/stats":
            stats(num_turns,total_in_toks,total_out_toks, messages)
            continue
        
        messages.append({"role":"user","content":user_input})
        result=client.complete(messages)
        messages.append({"role":"assistant","content":result["content"]})
        num_turns+=1 #increament
        total_in_toks+=result["input_tokens"]
        total_out_toks+=result["output_tokens"]
        
        print(f"assistant> {result['content']}")
        print(f"[turn {num_turns}] | input_tokens={result['input_tokens']} | output_tokens={result['output_tokens']} | totak_tokens={result['total_tokens']}")
        
if __name__ == "__main__":
    main()