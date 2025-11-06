from difflib import SequenceMatcher, get_close_matches
import os, json
from collections import defaultdict
import faiss, numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-mpnet-base-v2")
index = None
records, vectors = [], []

def load_json(path):
    if not os.path.exists(path): 
        return []
    with open(path, "r", encoding="utf-8") as f: 
        return json.load(f)

def normalize_string(s):
    return (s or "").strip().lower().replace("-", "").replace("_", "")

def find_best_match(rec, unified):
    """
    Find the best matching employee in unified dict using multiple heuristics:
    - Exact/normalized employee_id
    - Email match
    - Phone match
    - Full name fuzzy match
    Returns key in unified if found, else None.
    """
    eid_norm = normalize_string(rec.get("employee_id", ""))
    email = (rec.get("email") or "").lower()
    phone = (rec.get("phone") or "").lower()
    full_name_norm = normalize_string(rec.get("full_name", ""))

    # Try normalized employee_id
    if eid_norm in unified:
        return eid_norm

    # Try exact email
    for k, u in unified.items():
        if u.get("email", "").lower() == email and email:
            return k

    # Try exact phone
    for k, u in unified.items():
        if u.get("phone", "").lower() == phone and phone:
            return k

    # Try fuzzy full_name match
    names = [normalize_string(u.get("full_name", "")) for u in unified.values()]
    matches = get_close_matches(full_name_norm, names, n=1, cutoff=0.8)
    if matches:
        # Return key corresponding to the matched name
        for k, u in unified.items():
            if normalize_string(u.get("full_name", "")) == matches[0]:
                return k

    return None

def merge_records_on_the_fly(hrm_path="data/hrm.json", xops_path="data/xops.json", custom_path="data/custom.json"):
    hrm = load_json(hrm_path)
    xops = load_json(xops_path)
    custom = load_json(custom_path)
    unified = defaultdict(dict)

    # Load HRM as base
    for rec in hrm:
        eid_norm = normalize_string(rec.get("employee_id", ""))
        unified[eid_norm].update(rec)

    # Merge xOPS projects
    for rec in xops:
        key = find_best_match(rec, unified)
        if not key:
            # Create new entry if no match
            key = normalize_string(rec.get("employee_id", "new_" + str(len(unified)+1)))
        unified[key].setdefault("projects", [])
        for proj in rec.get("projects", []):
            unified[key]["projects"].append({
                "project_id": proj.get("project_id", ""),
                "project_name": proj.get("project_name", "") or "Unnamed Project",
                "role": proj.get("role", "Unknown role"),
                "responsibilities": proj.get("responsibilities", ""),
                "performance_metrics": proj.get("performance_metrics", {})
            })

    # Merge custom records (skills, endorsements, business context)
    for rec in custom:
        key = find_best_match(rec, unified)
        if not key:
            key = normalize_string(rec.get("employee_id", "new_" + str(len(unified)+1)))
        unified[key].setdefault("endorsements", [])
        unified[key].setdefault("skills", [])
        unified[key]["business_context"] = rec.get("business_context", unified[key].get("business_context", ""))
        unified[key]["endorsements"].extend(rec.get("endorsements", []))
        unified[key]["skills"].extend(rec.get("skills", []))

    # Build unified work_experience in chronological order
    for key, rec in unified.items():
        rec.setdefault("full_name", "Unknown")
        rec.setdefault("current_role", "Unknown")
        rec.setdefault("business_context", "")
        rec.setdefault("endorsements", [])
        rec.setdefault("skills", [])
        rec.setdefault("employment_history", [])
        rec.setdefault("education", "")
        rec.setdefault("projects", [])
        rec.setdefault("work_experience", [])

        work_exp = []

        # Add employment history
        for job in rec.get("employment_history", []):
            work_exp.append({
                "type": "employment",
                "role": job.get("role", "Unknown role"),
                "organization": job.get("organization", "Unknown"),
                "start_date": job.get("start_date"),
                "end_date": job.get("end_date"),
                "responsibilities": job.get("responsibilities", "")
            })

        # Add projects
        for proj in rec.get("projects", []):
            work_exp.append({
                "type": "project",
                "project_id": proj.get("project_id", ""),
                "project_name": proj.get("project_name", ""),
                "role": proj.get("role", ""),
                "responsibilities": proj.get("responsibilities", ""),
                "performance_metrics": proj.get("performance_metrics", {})
            })

        # Sort work_experience by start_date if available
        work_exp.sort(key=lambda x: x.get("start_date") or "9999-12-31")
        rec["work_experience"] = work_exp

    return list(unified.values())

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
    return model.encode([text])[0]

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
