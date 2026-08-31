import argparse, json, os, re, sys, time
from dataclasses import dataclass
from typing import List, Dict, Any, Iterable, Tuple

# from langchain_community.chat_models import ChatOllama #outdated caused error
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from collections import Counter

STOP ={ "the", "and", "for", "that", "with", "this", "from", "into", "than", "your", "you", "are", "was", "were", "have", "has", "had", "use", "used", "using", "about", "how", "can", "will", "more", "less", "very", "over", "under", "their", "there", "then", "out", "out", "on", "in", "of", "to", "by", "a", "an", "is", "it", "as",
}

# text cleanup and extraction
def strip_code_and_md(s:str) -> str:
    #removed fenced code blocks, inline backticks, normalize whitespace
    s= str(s)
    s=re.sub(r"```.*?```", " ", s, flags=re.DOTALL)
    s=re.sub(r"1([^`]*)", r"\1",s)
    return " ".join(s.split())

def extract_json_block(text: str) ->str:
    #assume its in json
    text=str(text).strip()
    first = text.find("{")
    if first == -1:
        return json.dumps({"message":strip_code_and_md(text)})
    try:
        obj,_=json.JSONDecoder().raw_decode(text[first:])
        return json.dumps(obj)
    except Exception:
        return json.dumps({"message":strip_code_and_md(text)})

	#return text

def tokens(txt: str) -> List[str]:
    # tokenize lowercase
    lowercased = re.findall(r"[a-z][a-z\-]+", str(txt).lower())
    return [l for l in lowercased if l not in STOP]

def ngrams(words: List[str], n:int) -> Iterable[Tuple[str, ...]]:
    for i in range(max(0, len(words)-n+1)):
	    yield tuple(words[i:i+n])

def phrase_candidates(title:str, content:str, maxn:int=12) -> List[str]:
    words=tokens(title) + tokens(content)
    if not words:
        return []
    c = Counter()
    for n in (2,3):
        for gram in ngrams(words,n):
            c[" ".join(gram)] +=1
    phrase = [p for p, _ in c.most_common()]
    
    if len(phrase) < maxn:
        for w, _ in Counter(words).most_common():
            if w not in phrase:
                phrase.append(w)
    
    return phrase[:maxn]

# output schema coercion
def coerce_reply(raw_obj: Any, title:str, content:str, strict:bool) -> Dict[str, Any]:
    if not isinstance(raw_obj, dict):
        raw_obj={}
    data=raw_obj.get("data", {})
    if not isinstance(data, dict):
        data ={}
    
    thought = str(raw_obj.get("thought", ""))
    message=strip_code_and_md(str(raw_obj.get("message","")))
    if not message:
        message = "no message"
    message = " ".join(message.split()[:60])
    candidates=phrase_candidates(title, content)
    tags=[]
    for t in data.get("tags", []) or []:
        if isinstance(t,str) and t.strip():
            t=strip_code_and_md(t).lower()
            if t not in tags:
                tags.append(t)
    
    for c in candidates:
        if len(tags)>=3: 
            break
        if c not in tags:
            tags.append(c)
    fillers = ["general topic", "key detail", "overview"]
    while len(tags)<3 and fillers:
        f=fillers.pop(0)
        if f not in tags:
            tags.append(f)
    tags = tags[:3]
    
    if strict:
        pool = [c for c in candidates if " " in c and c not in tags]
        for i,t in enumerate(tags):
            if sum(" " in tag for tag in tags) >=2:
                break
            if " " not in t and pool:
                tags[i] = pool.pop(0)
    summary = strip_code_and_md(str(data.get("summary", "")))
    if not summary:
        summary = f"{title}: {content}".strip(": ")
        
    summary= " ".join(summary.split()[:25]).rstrip(".!? ") + "."
    
    issues=[strip_code_and_md(str(i)) for i in (data.get("issues") or []) if str(i).strip()]
    
    return {
        "thought": thought,
        "message": message,
        "data":{"tags":tags, "summary":summary, "issues":issues},
    }
    
def parse_and_coerce(text: str, title: str, content: str, strict:bool) ->Dict[str, Any]:
    try:
        obj=json.loads(extract_json_block(text))
    except Exception:
        obj={"message":strip_code_and_md(text)}
    return coerce_reply(obj,title, content, strict)

#agent wrapper
@dataclass
class SimpleAgent:
    name:str
    system:str
    model:Any
    
    def respond(
        self, 
        converstation:List[Dict[str,str]],
        task:str,
        title:str,
        content:str,
        strict: bool,
    ) -> Dict[str,Any]:
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system),
            ("human",
             "Task:\n{task}\n\nConversation so far:\n{history}\n\n"
             "Return ONLY one JSON object (no code fences, no markdown, no explanations)."
             "Keys: thought (string), message (non-empty, <=60 words, no code),"
             "data.tags (array of exactly 3 topiccal tags),"
             "data.summary (<=25 words, no ellipes), data.issues (array). \n"
             "Do not add extra text outside JSON."
             ),
        ])
        
        history_text ="\n".join([f'{m["role"]}: {m["content"]}' for m in converstation]) or "(empty)"
        chain = prompt | self.model | StrOutputParser()
        
        raw=chain.invoke({"task": task, "history":history_text})
        return parse_and_coerce(raw, title, content, strict)
    
#CLI entrypoint
    
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--title", default="Your Blog Title Here")
    ap.add_argument("--content", default="Your blog post content goes here.")
    ap.add_argument("--email", default="student@example.com")
    ap.add_argument("--model", default=os.environ.get("SMOL_MODEL", "qwen3:8b"))
    ap.add_argument("--base_url", default=os.environ.get("OLLAM_URL", "http://localhost:11434"))
    ap.add_argument("--turns", type=int, default=1)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--temperature", type=float,default=0.0)
    args=ap.parse_args()
    
    try:
        llm=ChatOllama(
            model=args.model,
            temperature = args.temperature,
            base_url=args.base_url,
            num_ctx=2048,
            format="json",
        )
    except Exception:
        print(
            "Failed to intialize ChatOllam. IS Ollam running and the model available?\n"
            "Try: 'ollama serve' and 'olllam pull <your-model-tag>'.",
            file=sys.stderr,
        )
        raise
    planner = SimpleAgent(
        name="Planner",
        system = "Propose exactly 3 distinct, topical tags (prefer multi-word phrases) and a one-line summary for the blog post.",
        model=llm,
    )
    reviewer = SimpleAgent(
        name="Reviewer",
        system=(
            "Validate: tags topical and not generic; summary < 25 words; no code or markdown."
            "If issues, list in data.issues; otherwise echo cleaned tags/summary."
        ),
        model=llm,
    )
    finalizer = SimpleAgent(
        name="Finalizer",
        system=(
            "Use reviewer feedback to finalize. Output exactly 3 tags in data.tags and data.tags and the final summary in data.summary."
            "Set data.issues to []."
        ),
        model=llm,
    )
    task = (
        f'Given blog title "{args.title}" and content "{args.content}", produce exactly 3 topical tags'
        f'and a one-sentence summary in your own words. Email is {args.email}.'
    )
    transcript: List[Dict[str,str]] = []
    
    #planner
    t0=time.time()
    a=planner.respond(transcript, task, args.title, args.content, args.strict)
    t1=time.time()
    transcript.append({"role": "Planner", "content":a.get("message","")})
    print(f"\n--- Planner ({int((t1-t0)*1000)} ms) ---\n{json.dumps(a,indent=2)}")
    
    # reviewer
    t0=time.time()
    b=reviewer.respond(transcript, task, args.title, args.content, args.strict)
    t1=time.time()
    transcript.append({"role": "Reviewer", "content":a.get("message","")})
    print(f"\n--- Planner ({int((t1-t0)*1000)} ms) ---\n{json.dumps(a,indent=2)}")
    
    #finalizer
    final=finalizer.respond(transcript, task, args.title, args.content, args.strict)
    print(f"\n Finalized Output \n{json.dumps(final,indent=2)}")
    
    #publish package
    package = {
        "title":args.title,
        "email":args.email,
        "content":args.content,
        "agents": {"transcript": transcript, "final":final.get("data", {})},
        "submissionDate":time.strftime("%Y-%m-d%T%H:%M:%SZ",time.gmtime()),
    }
    print(f"\n Publish Package \n{json.dumps(package,indent=2)}")
        
if __name__ == "__main__":
    main()