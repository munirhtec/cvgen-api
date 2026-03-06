from pydantic import BaseModel
from typing import List, Dict

class QueryRequest(BaseModel):
    job_description: str
    top_k: int = 5

class EmployeeSuggestion(BaseModel):
    record: Dict
    similarity: float #percentage

class SuggestionsResponse(BaseModel):
    suggestions: List[EmployeeSuggestion]
