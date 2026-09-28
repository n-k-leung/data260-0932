import csv
import glob
import json
import os
import requests
import faiss
from sklearn.feature_extraction.text import TfidfVectorizer

def main():
  REFUSAL = "I cannot answer this question from the provided documents"
  BASE = os.path.dirname(os.path.abspath(__file__))
  RAW = os. path. join(BASE, "raw")

  os.makedirs(RAW, exist_ok=True)

  MODEL = "qwen3:8b"
  CHUNK_SIZE = 500
  CHUNK_OVERLAP = 50
  TOP_K = 3
  MIN_SCORE = 0.10

  printout = open(RAW + "/rag_retrieval_printouts.txt", "w", encoding="utf-8")

  def show(text):
    print(text)
    printout.write(text + "\n")
  #read every document to cut it into chunks
  chunks = []
  DOCS = os.path. join(BASE, "docs")
  for source in sorted(os.listdir(DOCS)):
    if not source.endswith(".txt"):
      continue
    path = os.path.join(DOCS, source)
    source = os.path.basename (path)
    text = open(path, encoding="utf-8").read()
    start = 0
    number = 0
    while True:
      chunks.append ({
      "chunk_id": source + "#" + str(number),
      "source": source,
      "text": text[start:start + CHUNK_SIZE],
      })
      number = number + 1
      if start + CHUNK_SIZE >= len(text):
        break
      start = start + CHUNK_SIZE - CHUNK_OVERLAP
      
  #chunk into a vector
  vectorizer = TfidfVectorizer(stop_words="english")
  vectors = vectorizer.fit_transform([c["text"] for c in chunks]).toarray().astype("float32")
  faiss.normalize_L2(vectors)
  index = faiss. IndexFlatIP(vectors. shape[1])
  index.add (vectors)

  #find the top-k chunks for a question, with their scores
  def retrieve(question, k):
    q = vectorizer.transform([question]).toarray().astype("float32")
    faiss.normalize_L2(q)
    scores, ids = index. search(q, k)
    results = []
    for score, i in zip(scores[0], ids[0]):
      results.append({
        "chunk_id": chunks[i]["chunk_id"],
        "source": chunks[i]["source"],
        "text": chunks[i]["text"],
        "score": round(float(score), 3),
      })

    return results

  def print_retrieval(qid, question, k, results):
    show(" === " + qid + " (top_k = " + str(k) + "): " + question)
    for n, r in enumerate(results, 1):
      show(" #" + str(n) + " score=" + str(r["score"]) + " source=" + r["source"] + " chunk_id=" + r["chunk_id"])
      show("      "+ r["text"].replace("\n", " ") [:150] + " ... ")

  #drop chunks with a low score
  def word_overlap(a, b):
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    return len(words_a & words_b) / len(words_a | words_b)

  def clean_chunks(results):
    kept = []
    for r in results:
      if r["score"] < MIN_SCORE:
        continue
      duplicate = False
      for k in kept:
        if word_overlap(r["text"], k["text"]) > 0.4:
          duplicate = True
      if not duplicate:
        kept.append(r)
    return kept

  #A = no RAG, B = basic RAG (raw top-k chunks), C = context-engineered RAG (cleaned chunks, labelled with their source,
  def prompt_a(question):
    return question

  def prompt_b(question, results):
    context = "\n\n".join(r["text"] for r in results)
    return "Context:\n" + context + "\n\nQuestion: " + question + "\nAnswer:"

  def prompt_c(question, results):
    context =""
    for n, r in enumerate(results, 1):
      context = context + "[" + str(n) + "] (source: " + r["source"] + ")\n" + r["text"] + "\n\n"
    if context == "":
      context = "(no relevant context found) \n\n"
    rules = ("Rules:\n"
      "1. Answer only from the context below.\n"
      "2. After each fact, cite the source number like [1]. \n"
      "3. If the context does not have enough evidence, reply exactly: " + REFUSAL + "\n\n")
    return rules + "Context:\n" + context + "Question: " + question + "\nAnswer:"

  # temperature 0 and the seed make the answers repeatable.
  def ask_llm(prompt):
    body = {"model": MODEL, "prompt": prompt, "stream": False,
    "options": {"temperature": 0, "seed": 932}}
    try:
      r = requests.post("http://localhost:11434/api/generate", json=body, timeout=300)
    except requests.exceptions.ConnectionError:
      print("Cannot reach Ollama. Start it and run: ollama pull " + MODEL)
      raise SystemExit(1)
    return r.json()["response"].strip()

  questions =[
    {"id": "Q1", "type": "answer in one chunk", "question": "How many days do we have to fix a Medium severity vulnerability?", "key_facts": ["30 days"], "answer_all": ["30"], "answer_any": [], "must_refuse": False},
    {"id": "Q2", "type": "answer needs two chunks", "question": "What CVSS score makes a vulnerability Critical, and how many days do we have to fix it?","key_facts": ["9.0 to 10.0", "within 7 days"], "answer_all": ["9.0", "7"], "answer_any": [], "must_refuse": False},
    {"id": "Q3", "type": "similar information across documents","question": "What is the deadline for fixing a Critical vulnerability?","key_facts": ["within 7 days", "within 24 hours"], "answer_all": ["7 days", "24 hours"], "answer_any": [], "must_refuse": False},
    {"id": "Q4", "type": "ambiguous", "question": "How long do we have to respond?", "key_facts": ["3 business days"], "answer_all": [], "answer_any": ["which", "clarify", "specify", "depends", "different", "several"], "must_refuse": False},
    {"id": "Q5", "type": "answer not in the documents", "question": "What is the yearly budget of the security team?", "key_facts": [], "answer_all": [], "answer_any": [], "must_refuse": True},
    {"id": "Q6", "type": "unrelated","question": "How do I bake a chocolate cake?", "key_facts": [], "answer_all": [], "answer_any": [], "must_refuse": True},
  ]

  def facts_found(results, facts):
    text = " ".join(r["text"] for r in results).lower()
    return [f for f in facts if f.lower() in text]

  def is_refusal(answer):
    words = ["cannot answer", "can't answer", "don't know", "do not know", "not in the provided"]
    return any(w in answer.lower() for w in words)

  def is_correct(q, answer):
    if q["must_refuse"]:
      return is_refusal(answer)
    ok = all(w.lower() in answer.lower() for w in q["answer_all"])
    if q["answer_any"]:
      ok = ok and any(w in answer.lower() for w in q["answer_any"])
    return ok
  show("MODEL = " + MODEL + " | SEED = 932 | chunks = " + str(len(chunks)) + " | chunk_size = " + str(CHUNK_SIZE) + " | overlap = " + str(CHUNK_OVERLAP))
  check_rows = []
  for q in questions:
    ks = [1, 3, 5] if q["id"] == "Q2" else [TOP_K]
    for k in ks:
      results = retrieve(q["question"], k)
      print_retrieval(q["id"], q["question"], k, results)
      found = facts_found(results, q["key_facts"])
      relevant = [r for r in results if facts_found([r], q["key_facts"])]
      if q["key_facts"]:
        correct = "yes" if len(found) == len(q["key_facts"]) else "no"
      else:
        correct = "n/a"
      show(" correct retrieval: " + correct + " | relevant chunks: " + str(len(relevant)) + " | irrelevant chunks: " + str(len(results) - len(relevant)))
      check_rows.append([q["id"], k, correct, len(relevant), len(results) - len(relevant), " ".join(r["chunk_id"] for r in results), " ".join(str(r["score"]) for r in results)])
  #A = no RAG, B = basic RAG (top-3 raw chunks), C = context-engineered RAG.
  comparison = []
  eval_rows = []
  for q in questions:
    raw_results = retrieve(q["question"], TOP_K)
    clean_results = clean_chunks(raw_results)
    prompts = {
    "A": (prompt_a(q["question"]), []),
    "B": (prompt_b(q["question"], raw_results), raw_results),
    "C": (prompt_c(q["question"], clean_results), clean_results),
    }
    for config in ["A", "B", "C"]:
      prompt, used = prompts[config]
      answer = ask_llm(prompt)
      print(q["id"], config, "->", answer[:100].replace("\n", " "))

      refused = is_refusal(answer)
      correct = is_correct(q, answer)
      #refusal is grounded when needed
      if q["must_refuse"]:
        grounded = refused
      else:
        text_used = " ".join(r["text"] for r in used).lower()
        grounded = correct and all(w.lower() in text_used for w in q["answer_all"]) and len(used) > 0
      if config == "C":
        fmt = ("[" in answer and "]" in answer) or refused
      else:
        fmt = "n/a"
      retrieval_ok = "n/a" if (config == "A" or not q["key_facts"]) else (
        "yes" if len(facts_found(used, q["key_facts"])) == len(q["key_facts"]) else "no")

      comparison.append({"question": q["id"], "config": config, "chunks_used": [r["chunk_id"] for r in used], "answer": answer})
      eval_rows.append([q["id"], config, retrieval_ok, correct, grounded, refused if q["must_refuse"] else "n/a", fmt])

  with open(RAW + "/rag_comparison.json", "w", encoding="utf-8") as f:
    json.dump({"model": MODEL, "seed": 932, "results": comparison}, f, indent=2)

  with open(RAW + "/rag_evaluation.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["question", "config", "correct_retrieval", "correct_answer", "grounded", "refused_when_needed", "format_ok"])
    w.writerows (eval_rows)

  q = questions[1]
  sweep_rows = []
  for k in [1, 3, 5]:
    raw_results = retrieve(q["question"], k)
    clean_results = clean_chunks(raw_results)
    for config in ["B", "C"]:
      if config == "B":
        used, prompt = raw_results, prompt_b(q["question"], raw_results)
      else:
        used, prompt = clean_results, prompt_c(q["question"], clean_results)
      answer = ask_llm(prompt)
      relevant = [r for r in used if facts_found([r], q["key_facts"])]
      print("sweep k =", k, config, "->", answer[:100].replace("\n", " "))
      sweep_rows.append([k, config, len(used), len(relevant), len(used) - len(relevant), is_correct(q, answer), answer.replace("\n", " ")])

  with open(RAW + "/rag_k_sweep.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["top_k", "config", "chunks_in_prompt", "relevant", "irrelevant", "correct_answer", "answer"])
    w.writerows (sweep_rows)

  summary = []
  for config in ["A", "B", "C"]:
    rows = [r for r in eval_rows if r[1] == config]
    accuracy = sum(1 for r in rows if r[3]) / 6
    faithful = sum(1 for r in rows if r[4]) / 6
    robust = sum(1 for r in rows if r[0] in ("Q5", "Q6") and r[5] is True) / 2
    fmt = sum(1 for r in rows if r[6] is True) / 6 if config == "C" else "n/a"
    summary.append([config, round(accuracy, 2), round(faithful, 2), fmt if fmt == "n/a" else round(fmt, 2), robust])

  with open(RAW + "/rag_evaluation_summary.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["config", "accuracy", "faithfulness", "format_compliance", "robustness"])
    w.writerows (summary)
  print("config | accuracy | faithfulness | format_compliance | robustness")
  for row in summary:
    print(row)

if __name__ == "__main__":
  main()