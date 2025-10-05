from fastapi import APIRouter, Body

router = APIRouter()

@router.post("/manual-review")
def manual_review(issue_data: dict = Body(...)):
    return {"status": "Resolved manually"}
