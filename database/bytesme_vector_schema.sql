CREATE SCHEMA IF NOT EXISTS analytics;

SET search_path TO analytics, public;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS product_embeddings (
    embedding_id SERIAL PRIMARY KEY,
    product_code VARCHAR(20) NOT NULL UNIQUE,
    vector_embedding vector(384),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);


