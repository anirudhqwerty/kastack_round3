# DataFlow Monitor

This project is a complete, real-time log analytics and ingestion pipeline. It uses a FastAPI backend to ingest log data, Supabase (Postgres) for staging, Prefect for ETL processing, and Elasticsearch for high-speed analytics and dashboarding.

## Core Technologies

- **Backend API:** FastAPI
- **Web Dashboard:** HTML, CSS, Chart.js
- **Data Staging:** Supabase (Postgres)
- **ETL/Processing:** Prefect
- **Analytics Database:** Elasticsearch 8.11.0
- **Containerization:** Docker

## How It Works (Data Workflow)

### Ingestion
A simulator (log_simulator.py) continuously sends log lines via WebSocket to the FastAPI server. The server dumps this raw data into the raw_data table in Supabase.

### ETL (Extract, Transform, Load)
A continuous loop runs the Prefect script (prefect_flows.py).

- The ingest_and_clean flow pulls from raw_data, parses each log line, and inserts the structured data into the cleaned_data table.
- The index_cleaned flow pulls from cleaned_data and bulk-indexes the records into Elasticsearch.

### Visualization

- The FastAPI server hosts the dashboard/index.html file.
- The dashboard automatically refreshes every 30 seconds.
- When it loads, JavaScript (script.js) makes API calls to /api/logs/*.
- FastAPI proxies these requests to Elasticsearch, which runs the aggregations and returns the latest data to populate the charts.

## Project Structure

```
DataFlow-Monitor/
│
├── .env
├── requirements.txt
├── log_simulator.py
│
├── fastapi_app/
│   └── main.py
│
├── prefect_flows/
│   └── flows.py
│
├── dashboard/
│   ├── index.html
│   ├── styles.css
│   └── script.js
│
├── sql/
│   └── schema.sql
│
└── sample_data/
    └── sample.log
```

## Setup and Installation

### 1. Prerequisites

- Python 3.10+ and pip
- Docker Desktop: Must be installed and running.
- Supabase Account: A free Supabase project.

### 2. Install Dependencies

In your project's root folder, create a Python virtual environment and install the required packages.

```bash
# Create a virtual environment
python -m venv venv

# Activate it (Windows)
.\venv\Scripts\activate
# (macOS/Linux)
# source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Configure Environment

**Supabase:**

- Go to your Supabase project's SQL Editor.
- Copy the contents of sql/schema.sql and run it to create your tables.
- Go to Project Settings > API.
- Find your Project URL and your service_role Key.

**.env File:**

Create a file named .env in the project root and add your credentials:

```
SUPABASE_URL=YOUR_SUPABASE_PROJECT_URL_HERE
SUPABASE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY_HERE
ELASTIC_URL=http://localhost:9200
```

## How to Run (Continuous Demo Workflow)

You will need four separate terminals open in your project's root directory.

### Terminal 1: Start Elasticsearch

Start the Elasticsearch container. This command disables security, making it accessible for local development.

```bash
docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" -e "xpack.security.enabled=false" elasticsearch:8.11.0
```

(Wait ~30 seconds for it to start up)

### Terminal 2: Start the FastAPI Server

Activate your virtual environment and start the uvicorn server. This serves both the API and the web dashboard.

```bash
uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8000
```

(Leave this running)

### Terminal 3: Start the Log Simulator

Activate your virtual environment and run the log_simulator.py script. This will start sending logs to your API.

```bash
python log_simulator.py
```

You will see it send a new log every 3 seconds. Leave this running.

### Terminal 4: Start the Continuous ETL Pipeline

Activate your virtual environment and run the Prefect flow in a continuous loop. This PowerShell command runs the script, waits 10 seconds, and repeats.

```bash
while (1) { python prefect_flows.py; Start-Sleep -Seconds 10 }
```

This will now check for new logs every 10 seconds and process them. Leave this running.

## Final Step: View Your Dashboard

Everything is now running in a continuous loop.

Go to your browser and open: http://localhost:8000

The dashboard auto-refreshes every 30 seconds. You will see the "Total Logs" count and other charts update automatically as new logs are ingested and processed.