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
        self.feedback_history = []  # This keeps a history of all feedbacks
        self.last_feedback = ""  # Latest feedback (for easy access)
        self.drafting_agent = DraftingAgent()
        self.review_agent = ReviewAgent()
        self.refinement_agent = RefinementAgent()

    def draft(self):
        """Generate the CV draft."""
        self.current_draft = self.drafting_agent.generate(self.original_record)
        return self.current_draft

    def review(self):
        """Review the current draft, and if no draft exists, generate it."""
        if not self.current_draft:
            self.draft()
        self.current_draft = self.review_agent.review(self.current_draft)
        return self.current_draft

    def refine(self):
        """Refine the current draft based on feedback and original data."""
        if not self.current_draft:
            self.draft()
        self.current_draft = self.refinement_agent.refine(self.current_draft, self.original_record)
        return self.current_draft

    def add_feedback(self, feedback_item):
        """
        Add feedback to both feedback history and feedback array.
        Feedback history stores all feedback, while feedback array stores the most recent feedback.
        """
        # Add feedback to feedback history (append to history)
        self.feedback_history.append(feedback_item)
                
        # Set the last feedback (same as current feedback)
        self.last_feedback = feedback_item

        # Initialize current draft if necessary
        if not self.current_draft:
            self.draft()

        # Refine the draft based on the new feedback
        self.current_draft = self.refinement_agent.refine(self.current_draft, self.original_record)

        # After refinement, update the lastFeedback field in the draft
        self.current_draft["lastFeedback"] = self.last_feedback

        # Ensure feedback history is updated in the draft
        self.current_draft["feedbackHistory"] = self.feedback_history

    def reset(self):
        """Reset the pipeline, clearing the draft and feedback."""
        self.current_draft = None
        self.feedback_history = []  # Clear the feedback history
        self.last_feedback = ""  # Reset last feedback

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
    
    # Add feedback, which will overwrite the feedback in the current draft
    pipeline.add_feedback(request.feedback)
    return {"success": True, "message": "Feedback applied", "draft": pipeline.current_draft}
    

@router.post("/reset/{employee_id}")
def reset_cv(employee_id: str):
    pipeline = pipelines.get(employee_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="No active pipeline")
    pipeline.reset()
    return {"success": True, "message": "Pipeline reset"}
