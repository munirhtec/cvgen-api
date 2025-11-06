from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query
from lib.llm import get_llm_response
from services.jd_extractor import extract_jd_from_url

router = APIRouter()

@router.get("/extract-jd")
async def extract_job_description(url: str = Query(..., description="URL to extract the job description from")):
    try:
        jd_text = extract_jd_from_url(url)
        return {"job_description": jd_text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error extracting job description: {str(e)}")

class QuestionRequest(BaseModel):
    question: str

@router.post("/ask")
def get_response_from_ai(request: QuestionRequest):
    answer = get_llm_response(request.question)
    return {"answer": answer.choices[0].message.content}
