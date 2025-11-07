import copy
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from typing import Dict
from services.rag_faiss import find_employee
from services.agents import DraftingAgent, ReviewAgent, RefinementAgent

router = APIRouter()
pipelines: Dict[str, "CVPipeline"] = {}

class CVPipeline:
    def __init__(self, employee_record):
        self.employee_id = str(employee_record["employee_id"])
        self.original_record = copy.deepcopy(employee_record)
        self.current_draft = None
        self.feedback_history = []
        self.drafting_agent = DraftingAgent()
        self.review_agent = ReviewAgent()
        self.refinement_agent = RefinementAgent()

    def draft(self):
        self.current_draft = self.drafting_agent.generate(self.original_record)
        return self.current_draft

    def review(self):
        if not self.current_draft:
            self.draft()
        self.current_draft = self.review_agent.review(self.current_draft)
        return self.current_draft

    def refine(self):
        if not self.current_draft:
            self.draft()
        self.current_draft = self.refinement_agent.refine(self.current_draft, self.original_record)
        return self.current_draft

    def add_feedback(self, feedback_item):
        """
        Add feedback to history and current draft, then refine CV based on it.
        Feedback is never erased.
        """
        self.feedback_history.append(feedback_item)

        if not self.current_draft:
            self.draft()
        if "feedback" not in self.current_draft:
            self.current_draft["feedback"] = []

        self.current_draft["feedback"].append(feedback_item)

        self.current_draft = self.refinement_agent.refine(self.current_draft, self.original_record)

    def reset(self):
        self.current_draft = None
        self.feedback_history = []


# FastAPI routes
@router.post("/start/{employee_query}")
def start_cv(employee_query: str):
    employee = find_employee(employee_query)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    pipeline = CVPipeline(employee)
    pipelines[str(employee["employee_id"])] = pipeline
    return {"message": "Draft created", "employee_id": pipeline.employee_id, "draft": pipeline.draft()}


@router.get("/draft/{employee_id}")
def get_draft(employee_id: str):
    pipeline = pipelines.get(employee_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="No active pipeline")
    return {"draft": pipeline.current_draft}


@router.post("/review/{employee_id}")
def review_cv(employee_id: str):
    pipeline = pipelines.get(employee_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="No active pipeline")
    return pipeline.review()


@router.post("/refine/{employee_id}")
def refine_cv(employee_id: str):
    pipeline = pipelines.get(employee_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="No active pipeline")
    return pipeline.refine()


class FeedbackRequest(BaseModel):
    employee_id: str
    feedback: str

@router.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    pipeline = pipelines.get(request.employee_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="No active pipeline")
    pipeline.add_feedback(request.feedback)
    return {"success": True, "message": "Feedback applied", "draft": pipeline.current_draft}


@router.post("/reset/{employee_id}")
def reset_cv(employee_id: str):
    pipeline = pipelines.get(employee_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="No active pipeline")
    pipeline.reset()
    return {"success": True, "message": "Pipeline reset"}
