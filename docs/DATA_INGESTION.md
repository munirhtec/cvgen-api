# Data Ingestion and Retrieval Strategy

This document outlines the strategy for ingesting employee data from multiple sources and retrieving it using Vector Search (RAG).

## Overview

The system aggregates data from three primary sources to create a unified 360-degree view of an employee:
1.  **HRM (Human Resource Management)**: Core personnel data (ID, name, role, history).
2.  **xOPS (Project Operations)**: Detailed project assignments, roles, and performance metrics.
3.  **Custom Data**: Skills, endorsements, and business context.

## Ingestion Pipeline (`services/rag_faiss.py`)

### 1. Unified Record Creation
Data is merged "on-the-fly" (or during ingestion) into a unified JSON structure.
- **Matching Logic**: Records are linked via `employee_id`. Fallback fuzzy matching is used on `full_name`, `email`, and `phone` to handle inconsistencies across systems.
- **Schema**:
    ```json
    {
      "employee_id": "...",
      "full_name": "...",
      "work_experience": [
        { "type": "employment", ... },
        { "type": "project", ... }
      ],
      "skills": [...],
      "endorsements": [...]
    }
    ```

### 2. Serialization for Embedding
To enable semantic search, the unified record is serialized into a text summary.
- **Summary Mode** (Default): Creates a natural language paragraph describing the employee's current role, key projects, and history. This is optimized for semantic matching against queries like "looking for a senior java developer with finance experience".
- **Detailed Mode**: Key-value pairs for more granular inspection.

### 3. Vectorization & Indexing
- **Embeddings**: We use an API-based embedding model (configurable via `Settings.embedding_model`, default: `l2-embedding`).
    - *Previous implementation used local `SentenceTransformer`, which has been replaced for consistency and scalability.*
- **Index**: FAISS (`IndexFlatIP`) is used for exact inner product search (cosine similarity on normalized vectors). This ensures high precision for retrieving the top relevant employees.

## Retrieval

### Semantic Search
- Queries are vectorized using the same API model.
- We retrieve the top-k (default: 5) most similar employee records.
- Results include a similarity score to gauge relevance.

### Fuzzy Search (Fallback)
- If vector search is not sufficient or for specific name lookups, a fuzzy string matching logic (`find_employee`) is available to find employees by name, email, or partial ID.

## Synthetic Data Generation
- A script `scripts/generate_data.py` provides synthetic data generation using LLMs to populate the system for testing and development.
