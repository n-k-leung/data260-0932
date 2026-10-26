import os

from app import file_mem as fm

TEST_DIR = os.path.join(os.path.dirname(__file__), "..", "testing")
ORIGINAL = os.path.join(TEST_DIR, "MEMORY_original.md")
CONSOLIDATED = os.path.join(TEST_DIR, "MEMORY_consolidated.md")
ARCHIVE = os.path.join(TEST_DIR, "MEMORY_archive.md")

original_text = fm.read_file(ORIGINAL)
total_before = len(original_text.splitlines())
print(
    "ORIGINAL: total lines =",
    total_before,
    "| non-empty non-comment lines =",
    fm.count_memory_lines(original_text),
)

needed, reason = fm.needs_consolidation(original_text)
print("needs consolidation:", needed, "->", reason)

if os.path.exists(ARCHIVE):
    os.remove(ARCHIVE)
new_text, report = fm.consolidate_text(original_text)
fm.write_file(CONSOLIDATED, new_text)
fm.write_file(ARCHIVE, "\n".join(report["archive_lines"]) + "\n")
total_after = len(new_text.splitlines())

print("\nconsolitated: total lines =", total_after)
print("duplicates merged:", len(report["duplicates"]))
print("contradictions resolved :", len(report["resolutions"]))
for r in report["resolutions"]:
    print(f"[{r['topic']}] kept ({r['kept']['date']}) {r['kept']['text']}")
    print(f"dropped ({r['dropped']['date']}) {r['dropped']['text']}")

print("\npossibly wrong resolutions (newest-wins picked a temporary exception):")
for r in report["suspect_resolutions"]:
    print(f"[{r['topic']}] kept: {r['kept']['text']}")
    print(f"should have kept: {r['dropped']['text']}")

print("\nchecks")
print("fewer than 40 lines:", total_after < 40, f"({total_after} lines)")
print("at least 3 duplicates merged:", len(report["duplicates"]) >= 3)
print("at least 3 contradictions found:", len(report["resolutions"]) >= 3)
print(
    "nothing silently deleted: ",
    len(report["archive_lines"]) - 1
    == len(report["duplicates"]) + len(report["resolutions"]),
    "(every removed fact is in MEMORY_archive.md)",
)
