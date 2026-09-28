from sqlalchemy import text
from app.database import engine

query = "EXPLAIN SELECT * FROM advisories WHERE vul_id = 42"
index_name = "idx_advisories_vul_id"

def run_explain(conn):
    result = conn.execute(text(query))
    lines = [" | ".join(result.keys())]
    for row in result.fetchall():
        lines.append(" | ".join(str(x) for x in row))
    return "\n".join(lines)

with engine.connect() as conn:
    try:
        conn.execute(text("DROP INDEX " + index_name + " ON advisories"))
        conn.commit()
    except Exception:
        conn.rollback()

    before = run_explain(conn)

    # add the one index
    conn.execute(text("CREATE INDEX " + index_name + " ON advisories (vul_id)"))
    conn.commit()

    after = run_explain(conn)

print(query)
print(" --- BEFORE (no index) --- ")
print(before)
print(" --- AFTER (index added) --- ")
print(after)

with open("../raw/explain_before.txt", "w") as f:
    f.write(query + "\n" + before + "\n")
with open("../raw/explain_after.txt", "w") as f:
    f.write(query + "\n" + after + "\n")