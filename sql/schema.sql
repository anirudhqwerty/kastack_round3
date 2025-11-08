-- Table to store raw incoming data
CREATE TABLE IF NOT EXISTS raw_data (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    payload TEXT NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster queries on unprocessed data
CREATE INDEX IF NOT EXISTS idx_raw_data_processed ON raw_data(processed) WHERE processed = FALSE;

-- Table to store cleaned/normalized data
CREATE TABLE IF NOT EXISTS cleaned_data (
    id BIGSERIAL PRIMARY KEY,
    raw_id BIGINT REFERENCES raw_data(id),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    level TEXT NOT NULL,
    host TEXT NOT NULL,
    message TEXT,
    meta JSONB,
    indexed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster queries on unindexed data
CREATE INDEX IF NOT EXISTS idx_cleaned_data_indexed ON cleaned_data(indexed) WHERE indexed = FALSE;

-- Indexes for analytics
CREATE INDEX IF NOT EXISTS idx_cleaned_data_timestamp ON cleaned_data(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_cleaned_data_level ON cleaned_data(level);
CREATE INDEX IF NOT EXISTS idx_cleaned_data_host ON cleaned_data(host);