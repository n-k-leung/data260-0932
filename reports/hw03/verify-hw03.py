import json
import os

def main():
    
    checks={}
    checks["dataset_folder_exists"] = os.path.isdir("dataset")
    checks["dataset_200kb_size"] = sum(os.path.getsize(os.path.join("dataset",f)) for f in os.listdir("dataset")) >= 200000
    checks["SOURCES_file_exists"] = os.path.exists("SOURCES.md")
    checks["corpus_manifest_exists"] = os.path.exists("CORPUS_MANIFEST.json")
    checks["questions_file_exists"] = os.path.exists("questions.yaml")
    checks["metrics_file_exists"] = os.path.exists("METRICS.md")
    
    checks["all_files_created_successfully"] = all(v for k, v in checks.items() if isinstance(v,bool))
    json.dump(checks,open("verification.json", "w"))
    print(json.dumps(checks))
if __name__=="__main__":
    main()