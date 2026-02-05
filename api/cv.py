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
        self.cv = None
        self.feedback_history = []
        self.last_feedback = ""
        self.drafting_agent = DraftingAgent()
        self.review_agent = ReviewAgent()
        self.refinement_agent = RefinementAgent()

    def draft(self):
        self.cv = self.drafting_agent.generate(self.original_record)
        return self.cv

    def review(self):
        self.cv = self.review_agent.review(self.cv)
        return self.cv

    def refine(self):
        self.cv = self.refinement_agent.refine(self.cv, self.original_record)
        return self.cv

    def add_feedback(self, feedback_item: str):
        self.feedback_history.append(feedback_item)
        self.last_feedback = feedback_item

        if not self.cv:
            self.draft()

        self.cv = self.review_agent.review(self.cv, feedback_item)

        # self.cv = self.refinement_agent.refine(self.cv, self.original_record)

        # Update lastFeedback and feedbackHistory
        self.cv["lastFeedback"] = self.last_feedback
        self.cv["feedbackHistory"] = self.feedback_history

    def reset(self):
        self.cv = None
        self.feedback_history = []
        self.last_feedback = ""

# FastAPI routes
@router.post("/start/{employee_query}")
def start_cv(employee_query: str):
    """
    Start CV generation with AUTOMATED 3-AGENT PIPELINE.
    
    This endpoint automatically runs the CV through all 3 agents:
    1. DraftingAgent: Creates initial CV from employee data
    2. ReviewAgent: Fact-checks and validates (anti-hallucination)
    3. RefinementAgent: Final polish and quality assurance
    
    This reduces hallucinations and improves overall quality.
    """
    employee = find_employee(employee_query)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    pipeline = CVPipeline(employee)
    pipelines[str(employee["employee_id"])] = pipeline
    
    # AUTOMATED 3-AGENT PIPELINE
    print(f"🚀 Starting automated CV generation for {employee.get('full_name', 'Unknown')}")
    
    # Step 1: Draft
    print("  📝 Step 1/3: Drafting...")
    draft_result = pipeline.draft()
    
    # Step 2: Review (fact-checking, anti-hallucination)
    print("  🔍 Step 2/3: Reviewing and fact-checking...")
    reviewed_result = pipeline.review()
    
    # Step 3: Refine (final quality assurance)
    print("  ✨ Step 3/3: Refining...")
    final_result = pipeline.refine()
    
    print(f"  ✅ CV generation complete!")
    
    return {
        "message": "CV generated through 3-agent pipeline (draft → review → refine)",
        "employee_id": pipeline.employee_id,
        "draft": final_result,
        "pipeline_stages": ["drafting", "review", "refinement"]
    }


@router.get("/draft/{employee_id}")
def get_draft(employee_id: str):
    pipeline = pipelines.get(employee_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="No active pipeline")
    return {"draft": pipeline.cv}


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
    return {"success": True, "message": "Feedback applied", "draft": pipeline.cv}
    

@router.post("/reset/{employee_id}")
def reset_cv(employee_id: str):
    pipeline = pipelines.get(employee_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="No active pipeline")
    pipeline.reset()
    return {"success": True, "message": "Pipeline reset"}
