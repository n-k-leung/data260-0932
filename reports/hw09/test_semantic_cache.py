from semantic_cache import SemanticResponseCache

QUERIES = [
    ("new", "What should our team do about CVE-2021-23337 in lodash 4.17.20?"),
    ("exact duplicate", "What should our team do about CVE-2021-23337 in lodash 4.17.20?"),
    ("paraphrase", "How should we handle the lodash 4.17.20 vulnerability CVE-2021-23337?"),
    ("new", "Which version of requests fixes CVE-2018-18074?"),
    ("exact duplicate", "Which version of requests fixes CVE-2018-18074?"),
    ("paraphrase", "What requests release patches CVE-2018-18074?"),
    ("new", "What is a software bill of materials (SBOM)?"),
    ("paraphrase", "Can you explain what an SBOM is?"),
    ("new", "How often should we scan our open source dependencies for vulnerabilities?"),
    ("exact duplicate", "How often should we scan our open source dependencies for vulnerabilities?"),
    ("new", "What does a CVSS score of 9.8 mean?"),
    ("paraphrase", "Explain what a CVSS rating of 9.8 means."),
]

def main():
    cache = SemanticResponseCache(threshold=0.85)
    #have to clear cache so can rerun and get same results
    cache.clear()

    results = []
    for number, (query_type, question) in enumerate(QUERIES, start=1):
        print(f"\nQuery {number} ({query_type})")
        response = cache.handle_query(question)
        results.append((query_type, response))
        print(f"is_cached: {response['is_cached']}")
        print(f"similarity: {response['similarity']}")
        print(f"latency: {response['latency_ms']} ms")
        print(f"answer: {response['answer']}")
        
    print("\nResults")
    for number, (query_type, r) in enumerate(results, start=1):
        print(f"{number}. {query_type}, is_cached: {r['is_cached']}, similarity: {r['similarity']}, latency: {r['latency_ms']} ms, question: {r['question']}")
    cached = [r for _, r in results if r["is_cached"]]
    not_cached = [r for _, r in results if not r["is_cached"]]
    hit_rate = len(cached) / len(results) * 100
    print(f"\nCache hit rate: {len(cached)} of {len(results)} ({hit_rate:.1f}%)")
    if cached:
        print(f"Average latency, cached: {sum(r['latency_ms'] for r in cached) / len(cached):.1f} ms")
    if not_cached:
        print(f"Average latency, not cached: {sum(r['latency_ms'] for r in not_cached) / len(not_cached):.1f} ms")

if __name__ == "__main__":
    main()