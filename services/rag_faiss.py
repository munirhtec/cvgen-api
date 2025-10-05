import os
import json
from collections import defaultdict
from typing import List, Dict, Tuple
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Load embedding model once (stronger model for higher semantic alignment)
model = SentenceTransformer("all-mpnet-base-v2")

# In-memory FAISS components
index = None
records = []  # List of full employee records
vectors = []  # List of normalized embedding vectors


def load_json(path: str) -> List[Dict]:
    if not os.path.exists(path):
        print(f"Warning: {path} not found, skipping.")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_records_on_the_fly(
    hrm_path="data/hrm.mock.json",
    xops_path="data/xops.mock.json",
    custom_path="data/custom.mock.json"
) -> List[Dict]:
    hrm = load_json(hrm_path)
    xops = load_json(xops_path)
    custom = load_json(custom_path)

    unified = defaultdict(dict)

    for rec in hrm:
        eid = rec.get("employee_id")
        if eid:
            unified[eid].update(rec)

    for rec in xops:
        eid = rec.get("employee_id")
        if eid:
            if "work_experience" not in unified[eid]:
                unified[eid]["work_experience"] = []
            unified[eid]["work_experience"].append({
                "project_id": rec.get("project_id", ""),
                "project_name": rec.get("project_name", ""),
                "role": rec.get("role", ""),
                "responsibilities": rec.get("responsibilities", ""),
                "performance_metrics": rec.get("performance_metrics", {})
            })

    for rec in custom:
        eid = rec.get("employee_id")
        if eid:
            if "business_context" not in unified[eid]:
                unified[eid]["business_context"] = rec.get("business_context", "")
            if "endorsements" not in unified[eid]:
                unified[eid]["endorsements"] = rec.get("endorsements", [])

    for eid, rec in unified.items():
        rec.setdefault("full_name", "")
        rec.setdefault("current_role", "")
        rec.setdefault("business_context", "")
        rec.setdefault("endorsements", [])
        rec.setdefault("work_experience", [])
        rec.setdefault("employment_history", [])
        rec.setdefault("education", "")

    return list(unified.values())


def generate_record_summary(record: Dict) -> str:
    """
    Generate a JD-style summary from an employee record for better semantic similarity.
    """
    summary = []

    name = record.get("full_name", "")
    role = record.get("current_role", "")
    context = record.get("business_context", "")
    education = record.get("education", "")
    if role:
        summary.append(f"{role} experienced in {context}.")

    if record.get("work_experience"):
        for xp in record["work_experience"]:
            proj = xp.get("project_name", "")
            responsibilities = xp.get("responsibilities", "")
            if proj or responsibilities:
                summary.append(f"Worked on '{proj}' project. {responsibilities}")

    if record.get("employment_history"):
        for job in record["employment_history"]:
            job_role = job.get("role", "")
            responsibilities = job.get("responsibilities", "")
            summary.append(f"Previously held role as {job_role}. {responsibilities}")

    if education:
        summary.append(f"Holds degree: {education}.")

    return " ".join(summary).strip().lower()


def serialize_record(record: Dict, mode: str = "summary") -> str:
    """
    Convert a record into an embedding-ready string.
    Modes:
    - "summary": natural language summary (better similarity)
    - "detailed": labeled field format (good for debugging)
    """
    if mode == "detailed":
        parts = [
            f"Name: {record.get('full_name', '')}",
            f"Role: {record.get('current_role', '')}",
            f"Business context: {record.get('business_context', '')}",
            "Endorsements: " + ", ".join(record.get("endorsements", [])),
            "Roles: " + ", ".join(x.get("role", "") for x in record.get("work_experience", [])),
            "Projects: " + ", ".join(x.get("project_name", "") for x in record.get("work_experience", [])),
            f"Education: {record.get('education', '')}"
        ]
        return " | ".join(parts).lower()
    else:
        return generate_record_summary(record)


def vectorize_text(text: str) -> np.ndarray:
    """Embed text to vector using the SentenceTransformer model."""
    return model.encode([text])[0]


def normalize(vec: np.ndarray) -> np.ndarray:
    """Normalize a vector to unit length."""
    norm = np.linalg.norm(vec)
    return vec if norm == 0 else vec / norm


def build_index(records_list: List[Dict], mode: str = "summary"):
    """
    Build FAISS index using normalized vectors from serialized records.
    """
    global index, vectors, records
    vectors = []
    records = []

    for record in records_list:
        text_blob = serialize_record(record, mode)
        vec = normalize(vectorize_text(text_blob))
        vectors.append(vec)
        records.append(record)

    if not vectors:
        raise ValueError("No vectors to index.")

    dim = len(vectors[0])
    index = faiss.IndexFlatIP(dim)  # Use inner product on normalized vectors = cosine sim
    index.add(np.array(vectors).astype("float32"))


def search_similar(query: str, top_k: int = 3) -> List[Tuple[int, float]]:
    """
    Search for top_k most similar employee records for the given query.
    Returns list of (index, similarity_score) tuples.
    """
    if index is None:
        raise ValueError("FAISS index not initialized.")

    q_vec = normalize(vectorize_text(query)).astype("float32").reshape(1, -1)
    scores, indices = index.search(q_vec, top_k)
    return [
        (int(idx), float(scores[0][i]))
        for i, idx in enumerate(indices[0])
        if idx != -1
    ]


def search_with_scores(query: str, top_k: int = 5) -> List[Dict]:
    """
    Return top_k records with similarity scores converted to percentage (0-100%).
    """
    results = []
    sims = search_similar(query, top_k)
    for idx, score in sims:
        rec = records[idx]
        similarity_pct = (score + 1) / 2 * 100  # Normalize [-1,1] to [0,100]
        results.append({
            "record": rec,
            "similarity": similarity_pct
        })
    return results


def search(query: str, top_k: int = 5) -> List[Dict]:
    """
    Public search API for retrieving top_k most similar records.
    """
    if index is None or not records:
        raise RuntimeError("Index is not built or records are empty.")
    return search_with_scores(query, top_k)


def get_records_by_indices(indices: List[int]) -> List[Dict]:
    return [records[i] for i in indices]


def preview_index(num_records: int = 5) -> List[Dict]:
    return records[:num_records] if records else []


def find_employee(query: str) -> Dict:
    """
    Search in-memory records by employee_id, full_name, or email (case-insensitive).
    """
    query_lower = query.lower()
    for rec in records:
        if (
            rec.get("employee_id", "").lower() == query_lower
            or rec.get("full_name", "").lower() == query_lower
            or rec.get("email", "").lower() == query_lower
        ):
            return rec
    return None
