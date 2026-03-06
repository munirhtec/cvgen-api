from typing import List, Optional, Any
from pydantic import BaseModel

# --- Synthetic Input Schemas (e.g. from HRM, XOPS, Custom sources) ---

class EmploymentHistoryItem(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    role: str
    responsibilities: List[str]

class HRMRecord(BaseModel):
    employee_id: str
    full_name: str
    email: str
    phone: str
    employment_history: List[dict]
    education: str

class ProjectInfo(BaseModel):
    project_id: str
    project_name: str
    role: str
    responsibilities: str
    performance_metrics: dict

class XOPSRecord(BaseModel):
    employee_id: str
    projects: List[ProjectInfo]

class CustomRecord(BaseModel):
    employee_id: str
    business_context: str
    skills: List[str]
    endorsements: List[str]

class SyntheticDataBatch(BaseModel):
    hrm: List[HRMRecord]
    xops: List[XOPSRecord]
    custom: List[CustomRecord]

# --- Unified and Indexed Schemas ---

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
