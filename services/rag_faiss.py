from difflib import SequenceMatcher, get_close_matches
import os, json
from collections import defaultdict
import faiss, numpy as np
from lib.llm import client, settings, get_llm_response
from lib.prompts import load_prompt
from pydantic import BaseModel
from typing import List, Optional, Any
from services import data_generator

# model = SentenceTransformer("all-mpnet-base-v2") # Removed local model
index = None
records, vectors = [], []

def load_json(path):
    if not os.path.exists(path): 
        return []
    with open(path, "r", encoding="utf-8") as f: 
        return json.load(f)

def normalize_string(s):
    return (s or "").strip().lower().replace("-", "").replace("_", "")



class UnifiedExperience(BaseModel):
    type: str  # "employment" or "project"
    role: Optional[str] = None
    organization: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    responsibilities: Optional[str] = ""
    performance_metrics: Optional[Any] = {}

class UnifiedRecord(BaseModel):
    employee_id: str
    full_name: str
    email: Optional[str] = ""
    phone: Optional[str] = ""
    current_role: Optional[str] = ""
    business_context: Optional[str] = ""
    skills: List[str] = []
    endorsements: List[str] = []
    education: Optional[str] = ""
    work_experience: List[UnifiedExperience] = []

class UnifiedRecordsList(BaseModel):
    records: List[UnifiedRecord]

def merge_records_on_the_fly(hrm_path="data/hrm.json", xops_path="data/xops.json", custom_path="data/custom.json"):
    # Try loading files first
    hrm = load_json(hrm_path)
    xops = load_json(xops_path)
    custom = load_json(custom_path)

    # If any essential data is missing, generate it dynamically
    if not hrm:
        print("⚠️ Data files not found or empty. Generating synthetic data...")
        batch = data_generator.generate_batch(5)
        hrm = [r.model_dump() for r in batch.hrm]
        xops = [r.model_dump() for r in batch.xops]
        custom = [r.model_dump() for r in batch.custom]
        print(f"✅ Generated {len(hrm)} synthetic records.")

    # Prepare data for LLM
    prompts = load_prompt("record_merging")
    user_prompt = prompts["user"].replace("{{ hrm_data }}", json.dumps(hrm, indent=2))
    user_prompt = user_prompt.replace("{{ xops_data }}", json.dumps(xops, indent=2))
    user_prompt = user_prompt.replace("{{ custom_data }}", json.dumps(custom, indent=2))

    print("Merging records using LLM...")
    try:
        response = get_llm_response(
            system_prompt=prompts["system"],
            user_prompt=user_prompt,
            temperature=0.2,
            response_model=UnifiedRecordsList
        )
        unified_list = response.parsed.records
        
        # Sort work_experience for each record
        for rec in unified_list:
            rec.work_experience.sort(key=lambda x: x.start_date or "9999-12-31")
            
        return [r.model_dump() for r in unified_list]
    except Exception as e:
        print(f"❌ Record merging failed: {e}")
        return []

def generate_record_summary(rec):
    s = []
    if rec.get("current_role"):
        s.append(f"{rec['current_role']} experienced in {rec.get('business_context','')}.")
    for xp in rec.get("work_experience", []):
        if xp.get("project_name") or xp.get("responsibilities"):
            s.append(f"Worked on '{xp.get('project_name','')}' project. {xp.get('responsibilities','')}")
    for job in rec.get("employment_history", []):
        s.append(f"Previously held role as {job.get('role','')}. {job.get('responsibilities','')}")
    if rec.get("education"):
        s.append(f"Holds degree: {rec['education']}.")
    return " ".join(s).strip().lower()

def serialize_record(rec, mode="summary"):
    if mode == "detailed":
        parts = [
            f"Name: {rec.get('full_name','')}",
            f"Role: {rec.get('current_role','')}",
            f"Business context: {rec.get('business_context','')}",
            "Endorsements: " + ", ".join(rec.get("endorsements", [])),
            "Skills: " + ", ".join(rec.get("skills", [])),
            "Roles: " + ", ".join(x.get("role", "") for x in rec.get("work_experience", [])),
            "Projects: " + ", ".join(x.get("project_name", "") for x in rec.get("work_experience", [])),
            f"Education: {rec.get('education','')}"
        ]
        return " | ".join(parts).lower()
    return generate_record_summary(rec)

def vectorize_text(text):
    text = text.replace("\n", " ")
    response = client.embeddings.create(input=[text], model=settings.embedding_model)
    return np.array(response.data[0].embedding, dtype="float32")

def normalize(vec):
    return vec if np.linalg.norm(vec) == 0 else vec / np.linalg.norm(vec)

def build_index(records_list, mode="summary"):
    global index, vectors, records
    vectors, records = [], []
    for rec in records_list:
        vec = normalize(vectorize_text(serialize_record(rec, mode)))
        vectors.append(vec)
        records.append(rec)
    if not vectors:
        raise ValueError("No vectors to index.")
    index = faiss.IndexFlatIP(len(vectors[0]))
    index.add(np.array(vectors).astype("float32"))

def search_similar(query, top_k=3):
    if index is None:
        raise ValueError("FAISS index not initialized.")
    q_vec = normalize(vectorize_text(query)).astype("float32").reshape(1, -1)
    scores, indices = index.search(q_vec, top_k)
    return [(int(idx), float(scores[0][i])) for i, idx in enumerate(indices[0]) if idx != -1]

def search_with_scores(query, top_k=5):
    return [
        {"record": records[idx], "similarity": (score + 1) / 2 * 100} 
        for idx, score in search_similar(query, top_k)
    ]

def search(query, top_k=5):
    if index is None or not records:
        raise RuntimeError("Index not built or records empty.")
    return search_with_scores(query, top_k)

def get_records_by_indices(indices):
    return [records[i] for i in indices]

def preview_index(num_records=5):
    return records[:num_records] if records else []

def find_employee(query, min_score=0.4):
    """
    Find an employee by ID, name, email, or phone, allowing typos and partial matches.
    Substring matches are prioritized over similarity ratio.
    min_score: minimum similarity for fuzzy match (0-1)
    """
    q_norm = normalize_string(query)
    best_match = None
    best_score = 0

    for rec in records:
        for field in ["employee_id", "full_name", "email", "phone"]:
            val_norm = normalize_string(rec.get(field, ""))

            if not val_norm:
                continue

            # Direct substring match first
            if q_norm in val_norm:
                return rec  # exact or partial substring found

            # Token-level match: check if any query token is in value
            q_tokens = q_norm.split()
            val_tokens = val_norm.split()
            token_overlap = sum(1 for t in q_tokens if any(t in vt for vt in val_tokens))
            if token_overlap / max(len(q_tokens), 1) > 0.5:
                return rec

            # Fallback to SequenceMatcher similarity
            score = SequenceMatcher(None, q_norm, val_norm).ratio()
            if score > best_score and score >= min_score:
                best_score = score
                best_match = rec

    return best_match
