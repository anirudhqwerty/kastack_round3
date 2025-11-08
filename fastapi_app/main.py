import os
import asyncio
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
# Add these new imports
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
# ---
from supabase import create_client
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_KEY in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="DataFlow Monitor - Ingest API")

class FileUploadResponse(BaseModel):
    inserted: int

# Simple dashboard proxy (queries ES)
from elasticsearch import Elasticsearch

ELASTIC_URL = os.getenv("ELASTIC_URL", "http://localhost:9200")
es = Elasticsearch([ELASTIC_URL])


# --- API ENDPOINTS ---

@app.post("/upload-file", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...), source: str = "file-upload"):
    # ... (your existing code for this function, no changes)
    content = (await file.read()).decode("utf-8", errors="ignore")
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    rows = []
    for line in lines:
        rows.append({"source": source, "payload": line})
    if not rows:
        raise HTTPException(status_code=400, detail="No lines found in file")
    res = supabase.table("raw_data").insert(rows).execute()
    inserted = len(rows)
    return {"inserted": inserted}


@app.websocket("/ws/logs")
async def websocket_logs(ws: WebSocket):
    # ... (your existing code for this function, no changes)
    await ws.accept()
    try:
        while True:
            text = await ws.receive_text()
            if not text.strip():
                continue
            supabase.table("raw_data").insert({
                "source": "ws-client",
                "payload": text
            }).execute()
            # optional ack
            await ws.send_text("OK")
    except WebSocketDisconnect:
        return


@app.get("/api/logs/over-time")
def logs_over_time(index="logs"):
    # ... (your existing code for this function, no changes)
    body = {
        "size": 0,
        "query": {"range": {"timestamp": {"gte": "now-60m"}}},
        "aggs": {
            "per_minute": {
                "date_histogram": {"field": "timestamp", "fixed_interval": "1m"}
            }
        }
    }
    res = es.search(index=index, body=body)
    buckets = res["aggregations"]["per_minute"]["buckets"]
    data = [{"ts": b["key_as_string"], "count": b["doc_count"]} for b in buckets]
    return JSONResponse(data)


@app.get("/api/logs/levels")
def logs_by_level(index="logs"):
    # ... (your existing code for this function, no changes)
    body = {
        "size": 0,
        "aggs": {"levels": {"terms": {"field": "level.keyword", "size": 10}}}
    }
    res = es.search(index=index, body=body)
    buckets = res["aggregations"]["levels"]["buckets"]
    return JSONResponse([{"level": b["key"], "count": b["doc_count"]} for b in buckets])


@app.get("/api/logs/top-hosts")
def top_hosts(index="logs"):
    # ... (your existing code for this function, no changes)
    body = {
        "size": 0,
        "aggs": {"hosts": {"terms": {"field": "host.keyword", "size": 10}}}
    }
    res = es.search(index=index, body=body)
    buckets = res["aggregations"]["hosts"]["buckets"]
    return JSONResponse([{"host": b["key"], "count": b["doc_count"]} for b in buckets])


app.mount("/static", StaticFiles(directory="dashboard"), name="static")

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("dashboard/index.html")