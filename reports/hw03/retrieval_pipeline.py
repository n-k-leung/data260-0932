import numpy as np
from sentence_transformers import SentenceTransformer
from llama_index.core.base.embeddings.base import BaseEmbedding
import json
import os
import time
import yaml
from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.core.node_parser import TokenTextSplitter, SentenceWindowNodeParser, SemanticSplitterNodeParser

class MiniLMEmbedding(BaseEmbedding):
    def __init__(self, model="sentence-transformers/all-MiniLM-L6-v2", **kwargs):
        super().__init__(**kwargs)
        self._model=SentenceTransformer(model)
        
    def _get_text_embedding(self, text):
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    def _get_query_embedding(self,query):
        embedding = self._model.encode(query,convert_to_numpy=True)
        return embedding.tolist()
    async def _aget_query_embedding(self, query):
        return self._get_query_embedding(query)
    

model = MiniLMEmbedding()
Settings.embed_model = model
#different chuncking
def token_node(docs):
    splitter=TokenTextSplitter(chunk_size=200,chunk_overlap=40)
    return splitter.get_nodes_from_documents(docs)

def semantic_node(docs):
    splitter=SemanticSplitterNodeParser(buffer_size=1, breakpoint_percentile_threshold=90, embed_model=model)
    return splitter.get_nodes_from_documents(docs)

def sentence_window_node(docs):
    splitter=SentenceWindowNodeParser.from_defaults(window_size=3, window_metadata_key="window", original_text_metadata_key="original_text")
    return splitter.get_nodes_from_documents(docs)

techniques= {"token": token_node, "semantic": semantic_node, "sentenceWindow": sentence_window_node}

#retrivel only helper to run one query against one technique
def cosine(a,b):
    a,b=np.array(a), np.array(b)
    denom=(np.linalg.norm(a) * np.linalg.norm(b))
    if denom ==0:
        return 0.0
    return float(np.dot(a,b)/denom)

#for top k nodes, auto to top 3
def run_query(technique, index, query, k=3):
    q=model.get_query_embedding(query)
    start = time.perf_counter()
    retriever = index.as_retriever(similarity_top_k=k)
    result = retriever.retrieve(query)
    latency = (time.perf_counter()-start)*1000
    rows=[]
    chunk_embeddings=[]
    for rank, node in enumerate(result, start=1):
        text=node.node.get_content()
        chunk_embedding=model.get_text_embedding(text)
        chunk_embeddings.append(chunk_embedding)
        rows.append({
            "technique": technique,
            "query": query,
            "rank": rank,
            "store_score": float(node.score) if node.score is not None else None,
            "cosine_sim": cosine(q,chunk_embedding),
            "chunk_len":len(text),
            #first ~160 characters of text preview
            "preview": text[:160].replace("\n", " "),
            "source_file": node.node.metadata.get("file_name", "")
        })
    matrix=np.array(chunk_embeddings) if chunk_embeddings else np.zeros((0,len(q)))
    print(f"\n{technique} | query: {query!r}")
    print(f"query vector shape: {np.array(q).shape}, first 8 values: {np.round(q[:8], 3)}")
    print(f"stacked vectors shape: {matrix.shape}")
    #print table for each technique
    print("rank, store_score, cosine_sim, chunk_len, preview")
    for r in rows:
        s=f"{r['store_score']:.3f}" if r["store_score"] is not None else "none"
        print(f"{r['rank']}, {s}, {r['cosine_sim']}, {r['chunk_len']}, {r['preview']}")
        
    return rows, latency

def main():
    doc=[]
    # load files from dataset
    dir = "dataset"
    for filename in sorted(os.listdir(dir)):
        if filename.endswith(".txt"):
            path=os.path.join(dir, filename)
            with open(path, encoding="utf-8") as f:
                text=f.read()
            doc.append(Document(text=text, metadata={"file_name":filename}))
        
    questions=[q["question"] for q in yaml.safe_load(open("questions.yaml"))]
    rows=[]
    chunk = {}
    
    for name, build in techniques.items():
        print(f"\n{name} index")
        nodes=build(doc)
        lengths=[len(n.get_content()) for n in nodes]
        chunk[name]= {"num_chunks": len(nodes), "avg_chunk_len":sum(lengths)/len(lengths)}
        print(f"{name}:{len(nodes)} chunks, avg length {chunk[name]['avg_chunk_len']:.0f} chars")
    
        index = VectorStoreIndex(nodes)
        latencies =[]
        for q in questions:
            query_rows, latency = run_query(name, index, q, k=3)
            for r in query_rows:
                r["latency"] = latency
            rows.extend(query_rows)
            latencies.append(latency)
        chunk[name]["mean_latency_ms"] = sum(latencies)/len(latencies)
        
    with open("raw/per_query_results.json", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
            
    with open("raw/per_technique_results.json", "w") as f:
        json.dump(chunk,f)
if __name__=="__main__":
    main()
    