from fastapi import APIRouter
from pydantic import BaseModel
from lib.llm import get_llm_response

router = APIRouter()

# Define a request model
class QuestionRequest(BaseModel):
    question: str

@router.post("/ask")
def get_response_from_ai(request: QuestionRequest):
    answer = get_llm_response(request.question)
    return {"answer": answer.choices[0].message.content}
