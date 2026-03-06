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

from models.api_helpers import QuestionRequest

from lib.prompts import load_prompt

@router.post("/ask")
def get_response_from_ai(request: QuestionRequest):
    prompts = load_prompt("ai_ask")
    user_prompt = prompts["user"].replace("{{ question }}", request.question)
    answer = get_llm_response(
        system_prompt=prompts["system"],
        user_prompt=user_prompt
    )
    return {"answer": answer.choices[0].message.content}
