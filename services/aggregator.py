import json
from pathlib import Path
from models.schemas import HRMRecord, XOPSRecord, CustomProfileRecord, UnifiedRecord
from typing import List, Dict


# Load JSON datasets
def load_dataset(path: str) -> List[dict]:
    with open(path) as f:
        return json.load(f)


# Normalize and merge records by employee_id
def merge_records(hrm_list, xops_list, custom_list) -> Dict[str, UnifiedRecord]:
    merged = {}

    for hrm in hrm_list:
        emp_id = hrm["employee_id"]
        merged[emp_id] = {
            "employee_id": emp_id,
            "full_name": hrm.get("full_name"),
            "contact": {"email": hrm.get("email"), "phone": hrm.get("phone")},
            "current_role": hrm.get("current_role"),
            "education": hrm.get("education", []),
            "work_experience": hrm.get("employment_history", []),
            "skills": [],
            "endorsements": [],
            "issues": []
        }

    for xops in xops_list:
        emp_id = xops["employee_id"]
        if emp_id not in merged:
            merged[emp_id] = {
                "employee_id": emp_id,
                "work_experience": [],
                "skills": [],
                "endorsements": [],
                "issues": ["Missing HRM data"]
            }

        # Add project data to work experience
        for proj in xops.get("projects", []):
            merged[emp_id]["work_experience"].append({
                "project": proj["project_name"],
                "role": proj["role"],
                "responsibilities": proj.get("responsibilities", []),
                "performance_metrics": proj.get("performance_metrics", [])
            })

    for custom in custom_list:
        emp_id = custom["employee_id"]
        if emp_id in merged:
            merged[emp_id]["business_context"] = custom.get("business_context")
            merged[emp_id]["endorsements"] = custom.get("team_contributions", [])
        else:
            # Handle conflict — employee present only in custom file
            merged[emp_id] = {
                "employee_id": emp_id,
                "work_experience": [],
                "business_context": custom.get("business_context"),
                "endorsements": custom.get("team_contributions", []),
                "issues": ["Missing HRM and xOPS data"]
            }

    return merged
