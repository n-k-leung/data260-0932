from app.database import SessionLocal
from app.models import Vul
from semantic_cache import SemanticResponseCache

SEVERITIES = ["Critical", "High", "Medium", "Low"]

def record_context(vul):
    return (f"Database record from s0932_rel (vulnerabilities table): id={vul.id}, "
            f"package_name={vul.package_name}, vul_code={vul.vul_code}, severity={vul.severity}. "
            f"Answer using this record.")

def update_severity(db, vul, new_severity, cache, bump_version):
    old_severity = vul.severity
    vul.severity = new_severity
    db.commit()
    print(f"Updated s0932_rel vulnerabilities id={vul.id}: severity {old_severity} -> {new_severity}")
    if bump_version:
        print(f"Data version is now {cache.bump_data_version()}")

def show(response):
    print(f"is_cached: {response['is_cached']}")
    print(f"similarity: {response['similarity']}")
    print(f"data_version: {response['data_version']}")
    print(f"answer: {response['answer']}")

def main():
    db = SessionLocal()
    vul = db.query(Vul).order_by(Vul.id.asc()).first()
    original_severity = vul.severity
    other_severities = [s for s in SEVERITIES if s != original_severity]
    question = f"What severity does our database list for {vul.vul_code} in {vul.package_name}?"
    cache = SemanticResponseCache(check_data_version=False)
    cache.clear()
    print("\nirst question (miss, the answer is stored)")
    show(cache.handle_query(question, context=record_context(vul)))
    print("\nupdate the record (no invalidation)")
    update_severity(db, vul, other_severities[0], cache, bump_version=False)
    print("\nsame question again (stale hit)")
    show(cache.handle_query(question, context=record_context(vul)))
    print(f"The database now says severity {vul.severity}, but the cached answer is from before the update.")
    print("\ninvalidation with the data-version marker")
    cache.check_data_version = True
    update_severity(db, vul, other_severities[1], cache, bump_version=True)
    show(cache.handle_query(question, context=record_context(vul)))
    update_severity(db, vul, original_severity, cache, bump_version=True)
    db.close()

if __name__ == "__main__":
    main()
