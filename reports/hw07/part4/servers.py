import os
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from agent import run_agent

HERE = os.path.dirname(os.path.abspath(__file__))
app = FastAPI(title="Bike share advisor")

@app.get("/")
def home():
    return FileResponse(os.path.join(HERE, "ui.html"))

@app.post("/run")
def run(csv_file: UploadFile = File(...), pricing_url: str = Form(...)):
    try:
        df = pd.read_csv(csv_file.file)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Could not read the CSV: " + str(e))
    scenario = os.path.splitext(csv_file.filename or "run")[0]
    scenario = "".join(c if c.isalnum() or c in "_-" else "_" for c in scenario)
    try:
        return run_agent(df, pricing_url, scenario)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail="Agent failed: " + str(e))