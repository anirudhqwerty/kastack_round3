import os
from prefect import flow, task, get_run_logger
from supabase import create_client
from dotenv import load_dotenv
from dateparser import parse as parse_date
from elasticsearch import Elasticsearch, helpers

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ELASTIC_URL = os.getenv("ELASTIC_URL", "http://localhost:9200")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
es = Elasticsearch([ELASTIC_URL])

@task
def fetch_unprocessed_raw(limit=500):
    # Grab raw rows not yet processed
    res = supabase.table("raw_data").select("*").eq("processed", False).limit(limit).execute()
    return res.data or []

def parse_line(line):
    # Example: simple parsing for "2025-11-07 12:15:30,ERROR,host1,Something happened"
    # Or if JSON given, try parse JSON
    import json
    out = {"timestamp": None, "level": None, "host": None, "message": line, "meta": {}}
    try:
        j = json.loads(line)
        out["message"] = j.get("message") or str(j)
        out["level"] = j.get("level")
        out["host"] = j.get("host")
        out["meta"] = j
        if "timestamp" in j:
            out["timestamp"] = parse_date(j["timestamp"])
    except Exception:
        # naive CSV split
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 4:
            maybe_ts = parts[0]
            ts = parse_date(maybe_ts)
            if ts:
                out["timestamp"] = ts
                out["level"] = parts[1]
                out["host"] = parts[2]
                out["message"] = ",".join(parts[3:])
    # fallback: timestamp now
    if out["timestamp"] is None:
        from datetime import datetime
        out["timestamp"] = datetime.utcnow()
    return out

@task
def clean_and_insert(raw_rows):
    out_rows = []
    for r in raw_rows:
        parsed = parse_line(r["payload"])
        out_rows.append({
            "raw_id": r["id"],
            "timestamp": parsed["timestamp"].isoformat(),
            "level": parsed["level"] or "INFO",
            "host": parsed["host"] or "unknown",
            "message": parsed["message"],
            "meta": parsed["meta"]
        })
    if out_rows:
        supabase.table("cleaned_data").insert(out_rows).execute()
        # mark raw rows processed
        raw_ids = [r["id"] for r in raw_rows]
        supabase.table("raw_data").update({"processed": True}).in_("id", raw_ids).execute()
    return len(out_rows)

@task
def fetch_unindexed_cleaned(limit=500):
    res = supabase.table("cleaned_data").select("*").eq("indexed", False).limit(limit).execute()
    return res.data or []

@task
def index_to_es(clean_rows, index_name="logs"):
    if not clean_rows:
        return 0
    # map to ES docs
    actions = []
    for r in clean_rows:
        doc = {
            "_index": index_name,
            "_id": r["id"],
            "_source": {
                "raw_id": r["raw_id"],
                "timestamp": r["timestamp"],
                "level": r["level"],
                "host": r["host"],
                "message": r["message"],
                "meta": r.get("meta", {}),
            }
        }
        actions.append(doc)
    helpers.bulk(es, actions)
    # mark indexed
    ids = [r["id"] for r in clean_rows]
    supabase.table("cleaned_data").update({"indexed": True}).in_("id", ids).execute()
    return len(actions)

@flow(name="ingest-and-clean")
def ingest_and_clean():
    logger = get_run_logger()
    raw = fetch_unprocessed_raw()
    n = clean_and_insert(raw)
    logger.info(f"cleaned {n} rows")

@flow(name="index-cleaned-to-es")
def index_cleaned():
    logger = get_run_logger()
    clean = fetch_unindexed_cleaned()
    n = index_to_es(clean)
    logger.info(f"indexed {n} docs to ES")
