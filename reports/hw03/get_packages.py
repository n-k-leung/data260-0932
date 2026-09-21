import json
import urllib.request
import hashlib
from datetime import date

packages=[
    "flask/0.12",
    "numpy/1.21.0",
    "cryptography/3.2",
    "pyyaml/5.3",
    "jinja2/2.4.1",
    "django/1.11.28",
    "lxml/4.6.2",
    "pillow/8.2.0",
    "requests/2.3.0",
    "urllib3/1.24.1",
    "twisted/18.4.0",
    "paramiko/2.4.1",
]

def get_version(version):
    url=f"https://pypi.org/pypi/{version}/json"
    with urllib.request.urlopen(url) as r:
        return json.load(r)
    
def get_sha(path):
    with open(path, "rb") as f:
        files_byte=f.read()
    return hashlib.sha256(files_byte).hexdigest()
    
def main():
    sources=[]
    manifest=[]
    access_date=date.today().isoformat()
    for p in packages:
        data=get_version(p)
        name = data["info"]["name"]
        vuls = data.get("vulnerabilities", [])
        lines= [f"package: {name} (version:{p})", f"vulnerability count: {len(vuls)}",""]
        for v in vuls:
            lines.append(f"id: {v.get('id')}")
            lines.append(f"aliases: {', '.join(v.get('aliases', []))}")
            lines.append(f"summary: {v.get('summary', '')}")
            lines.append(f"details: {v.get('details', '')}")
            fixed=[]
            for f in v.get("fixed_in", []):
                fixed.append(f)
            lines.append(f"vulnerability fixed in versions: {', '.join(fixed)}")
            links=[l.get('url','') for l in v.get('link',[])] if isinstance(v.get('link'),list) else []
            lines.append("links: " + ", ".join(links))
            lines.append("---------------------------")
            
        text="\n".join(lines)
        fname=f"dataset/{name}.txt"
        #UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 2112: character maps to <undefined> so used encoding utf-8
        with open(fname, "w", encoding="utf-8") as f:
            f.write(text)
        byte_size=len(text)
        file_hash=get_sha(fname)
        source_url = f"https://pypi.org/pypi/{p}/json"
        sources.append({
            "package": name,
            "version": p.split("/",1)[1],
            "url": source_url,
            "accessed": access_date
        })
        manifest.append({
            "filename": fname.replace("\\", "/"),
            "byte_size": byte_size,
            "sha256": file_hash
        })
        print(f"{name}.txt, bytes: {len(text)}, number of vuls: {len(vuls)}")
    
    with open("SOURCES.md", "w", encoding="utf-8") as f:
        f.write("| Package | Version | Source URL | Accessed | \n")
        f.write("|---------|---------|------------|----------|\n")
        for source in sources:
            f.write(
                f"| {source['package']} | {source['version']} | {source['url']} | {source['accessed']} |\n"
            )
    print("SOURCES.md created")
    
    with open("CORPUS_MANIFEST.json", "w", encoding="utf-8") as f:
        json.dump(manifest,f)
    print("CORPUS_MANIFEST.json created")
    
if __name__=="__main__":
    main()