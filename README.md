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

**Ingestion:** Log files are uploaded via a POST request (or WebSocket) to the FastAPI server. The server dumps this raw data into the `raw_data` table in Supabase.

**ETL (Extract, Transform, Load):** The Prefect script (`prefect_flows/flows.py`) is run.

- The `ingest_and_clean` flow pulls from `raw_data`, parses each log line, and inserts the structured data into the `cleaned_data` table.
- The `index_cleaned` flow pulls from `cleaned_data` and bulk-indexes the records into Elasticsearch.

**Visualization:**

- The FastAPI server hosts the `dashboard/index.html` file.
- When you load the page, the JavaScript (`script.js`) makes API calls to `/api/logs/*`.
- FastAPI proxies these requests to Elasticsearch, which runs the aggregations and returns the data to populate the charts.

## Project Structure

```
DataFlow-Monitor/
│
├── .env                # (You will create this)
├── requirements.txt    # (You will create this)
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
- Copy the contents of `sql/schema.sql` and run it to create your tables.
- Go to Project Settings > API.
- Find your Project URL and your service_role Key.

**.env File:**

- Create a file named `.env` in the project root.
- Add your credentials and the (default) Elastic URL.

```
SUPABASE_URL=YOUR_SUPABASE_PROJECT_URL_HERE
SUPABASE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY_HERE
ELASTIC_URL=http://localhost:9200
```

## How to Run (The Workflow)

You will need four separate terminals open in your project's root directory.

### Terminal 1: Start Elasticsearch

Start the Elasticsearch container. This command disables security, making it accessible for local development.

```bash
docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" -e "xpack.security.enabled=false" elasticsearch:8.11.0
```

(Wait ~30 seconds for it to start up)

### Terminal 2: Start the FastAPI Server

Activate your virtual environment (`.\venv\Scripts\activate`) and start the uvicorn server. This serves both the API and the web dashboard.

```bash
uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8000
```

(Leave this running)

### Terminal 3: Ingest Sample Data

Activate your virtual environment and use `curl.exe` to upload the sample log file to your running API.

```bash
# (Make sure venv is active in this terminal too)
curl.exe -X POST -F "file=@sample_data/sample.log" http://localhost:8000/upload-file
```

You should see a response: `{"inserted":30}`

### Terminal 4: Run the ETL Pipeline

Activate your virtual environment and run the Prefect flow. This will process the 30 raw logs from Supabase and push them to Elasticsearch.

```bash
# (Make sure venv is active in this terminal too)
python prefect_flows/flows.py
```

You should see output like "Indexed 30 documents into Elasticsearch."

## Final Step: View Your Dashboard

Everything is now running and the data is processed.

Go to your browser and open: http://localhost:8000