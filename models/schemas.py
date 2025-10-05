from typing import List, Optional
from pydantic import BaseModel


# ---------- Synthetic Input Schemas ----------
class EmploymentHistoryItem(BaseModel):
    start_date: str
    end_date: str
    role: str
    responsibilities: List[str]


class HRMRecord(BaseModel):
    employee_id: str
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    current_role: Optional[str]
    employment_history: List[EmploymentHistoryItem]
    education: List[str]


class ProjectItem(BaseModel):
    project_id: str
    project_name: str
    role: str
    responsibilities: List[str]
    performance_metrics: Optional[List[str]]


class XOPSRecord(BaseModel):
    employee_id: str
    projects: List[ProjectItem]


class CustomProfileRecord(BaseModel):
    employee_id: str
    business_context: str
    team_contributions: List[str]


# ---------- Unified Schema ----------
class UnifiedRecord(BaseModel):
    employee_id: str
    full_name: Optional[str]
    contact: Optional[dict]
    current_role: Optional[str]
    education: Optional[List[str]]
    work_experience: List[dict]  # Ordered + merged employment and project history
    skills: Optional[List[str]]
    endorsements: Optional[List[str]]
    business_context: Optional[str]
    issues: Optional[List[str]]
