import os
import json
from datetime import datetime
from typing import List, Dict, Any

from prefect import flow, task, get_run_logger
from supabase import create_client
from dotenv import load_dotenv
from dateparser import parse as parse_date
from elasticsearch import Elasticsearch, helpers

# -------------------------------------------------------------------
# Environment setup
# -------------------------------------------------------------------
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ELASTIC_URL = os.getenv("ELASTIC_URL", "http://localhost:9200")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError("Missing Supabase credentials in .env file.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
es = Elasticsearch([ELASTIC_URL])

# -------------------------------------------------------------------
# Utility functions
# -------------------------------------------------------------------

def parse_line(line: str) -> Dict[str, Any]:
    """
    Parse a single log line into its components.
    Expected format:
        <TIMESTAMP>,<LEVEL>,<HOST>,<MESSAGE>
    Example:
        2025-11-08 09:31:15,ERROR,Server-1,Database connection failed
    Falls back to current timestamp and generic defaults if parsing fails.
    """

    parsed = {
        "timestamp": None,
        "level": None,
        "host": None,
        "message": None,
        "meta": {}
    }

    # Try JSON log line
    try:
        j = json.loads(line)
        parsed["timestamp"] = parse_date(j.get("timestamp", "")) or datetime.utcnow()
        parsed["level"] = j.get("level", "INFO")
        parsed["host"] = j.get("host", "unknown")
        parsed["message"] = j.get("message", "")
        parsed["meta"] = j
        return parsed
    except Exception:
        pass

    # Try comma-separated 4 attributes
    parts = [p.strip() for p in line.split(",", 3)]
    if len(parts) == 4:
        ts_str, level, host, msg = parts
        parsed["timestamp"] = parse_date(ts_str) or datetime.utcnow()
        parsed["level"] = level or "INFO"
        parsed["host"] = host or "unknown"
        parsed["message"] = msg
    else:
        # Fallback: raw line as message
        parsed["timestamp"] = datetime.utcnow()
        parsed["level"] = "INFO"
        parsed["host"] = "unknown"
        parsed["message"] = line

    return parsed


# -------------------------------------------------------------------
# Prefect Tasks
# -------------------------------------------------------------------

@task(retries=3, retry_delay_seconds=5)
def fetch_unprocessed_raw(limit: int = 500) -> List[Dict[str, Any]]:
    """Fetch rows from raw_data where processed=False."""
    res = supabase.table("raw_data").select("*").eq("processed", False).limit(limit).execute()
    return res.data or []


@task
def clean_and_insert(raw_rows: List[Dict[str, Any]]) -> int:
    """Clean raw rows and insert into cleaned_data table."""
    if not raw_rows:
        return 0

    cleaned = []
    for r in raw_rows:
        parsed = parse_line(r["payload"])
        cleaned.append({
            "raw_id": r["id"],
            "timestamp": parsed["timestamp"].isoformat(),
            "level": parsed["level"],
            "host": parsed["host"],
            "message": parsed["message"],
            "meta": parsed["meta"]
        })

    supabase.table("cleaned_data").insert(cleaned).execute()

    raw_ids = [r["id"] for r in raw_rows]
    supabase.table("raw_data").update({"processed": True}).in_("id", raw_ids).execute()

    return len(cleaned)


@task(retries=3, retry_delay_seconds=5)
def fetch_unindexed_cleaned(limit: int = 500) -> List[Dict[str, Any]]:
    """Fetch cleaned_data rows where indexed=False."""
    res = supabase.table("cleaned_data").select("*").eq("indexed", False).limit(limit).execute()
    return res.data or []


@task
def index_to_elasticsearch(clean_rows: List[Dict[str, Any]], index_name: str = "logs") -> int:
    """Index cleaned rows into Elasticsearch and mark them as indexed."""
    if not clean_rows:
        return 0

    actions = []
    for r in clean_rows:
        actions.append({
            "_index": index_name,
            "_id": r["id"],
            "_source": {
                "raw_id": r["raw_id"],
                "timestamp": r["timestamp"],
                "level": r["level"],
                "host": r["host"],
                "message": r["message"],
                "meta": r.get("meta", {})
            }
        })

    helpers.bulk(es, actions)

    ids = [r["id"] for r in clean_rows]
    supabase.table("cleaned_data").update({"indexed": True}).in_("id", ids).execute()

    return len(actions)


# -------------------------------------------------------------------
# Prefect Flows
# -------------------------------------------------------------------

@flow(name="ingest-and-clean")
def ingest_and_clean():
    """Fetch new raw data, clean, and insert into cleaned_data."""
    logger = get_run_logger()
    raw = fetch_unprocessed_raw()
    count = clean_and_insert(raw)
    logger.info(f"Cleaned and inserted {count} rows into cleaned_data.")


@flow(name="index-cleaned-to-es")
def index_cleaned():
    """Fetch cleaned data, index into Elasticsearch, and mark indexed."""
    logger = get_run_logger()
    clean = fetch_unindexed_cleaned()
    count = index_to_elasticsearch(clean)
    logger.info(f"Indexed {count} documents into Elasticsearch.")


# -------------------------------------------------------------------
# Local execution entry point
# -------------------------------------------------------------------

if __name__ == "__main__":
    # For manual testing or running via cron
    ingest_and_clean()
    index_cleaned()
