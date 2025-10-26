from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict
from services import rag_faiss

router = APIRouter()

@router.post("/load")
async def load_and_build_faiss_index():
    try:
        records = rag_faiss.merge_records_on_the_fly()
        rag_faiss.build_index(records)
        return {"message": f"Loaded and indexed {len(records)} employee records dynamically."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preview")
async def preview_index(k: int):
    try:
        preview = rag_faiss.preview_index(k)
        return {"index_preview": preview}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/employee")
async def get_employee(query: str = Query(..., description="Employee ID, full name or email")):
    employee = rag_faiss.find_employee(query)
    if employee:
        return {"employee": employee}
    else:
        raise HTTPException(status_code=404, detail="Employee not found")

class QueryRequest(BaseModel):
    job_description: str
    top_k: int = 5

class EmployeeSuggestion(BaseModel):
    record: Dict  # Consider defining a detailed model if needed
    similarity: float  # Similarity percentage

class SuggestionsResponse(BaseModel):
    suggestions: List[EmployeeSuggestion]

@router.post("/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(request: QueryRequest):
    try:
        results = rag_faiss.search(request.job_description, request.top_k)
        # results is expected as list of dicts with 'record' and 'similarity' keys
        return {"suggestions": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
