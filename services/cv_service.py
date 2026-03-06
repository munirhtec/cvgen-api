import copy
from typing import Dict, List, Optional
from services.agents import DraftingAgent, ReviewAgent, RefinementAgent

class CVPipeline:
    def __init__(self, employee_record: dict):
        self.employee_id = str(employee_record["employee_id"])
        self.original_record = copy.deepcopy(employee_record)
        self.cv: Optional[dict] = None
        self.feedback_history: List[str] = []
        self.last_feedback: str = ""
        self.drafting_agent = DraftingAgent()
        self.review_agent = ReviewAgent()
        self.refinement_agent = RefinementAgent()

    def draft(self, log_cb=None) -> dict:
        self.cv = self.drafting_agent.generate(self.original_record, log_cb=log_cb)
        return self.cv

    def review(self, log_cb=None) -> dict:
        self.cv = self.review_agent.review(self.cv, log_cb=log_cb)
        return self.cv

    def refine(self, log_cb=None) -> dict:
        self.cv = self.refinement_agent.refine(self.cv, self.original_record, log_cb=log_cb)
        return self.cv

    def add_feedback(self, feedback_item: str, log_cb=None):
        self.feedback_history.append(feedback_item)
        self.last_feedback = feedback_item

        if not self.cv:
            self.draft(log_cb=log_cb)

        self.cv = self.review_agent.review(self.cv, feedback=feedback_item, employee_record=self.original_record, log_cb=log_cb)
        
        # We also need refinement step on feedback
        self.cv = self.refinement_agent.refine(self.cv, self.original_record, log_cb=log_cb)
        
        # Update lastFeedback and feedbackHistory labels in the dict for UI
        if self.cv and isinstance(self.cv, dict):
            self.cv["lastFeedback"] = self.last_feedback
            self.cv["feedbackHistory"] = self.feedback_history

    def reset(self):
        self.cv = None
        self.feedback_history = []
        self.last_feedback = ""

# Global pipeline state manager
pipelines: Dict[str, CVPipeline] = {}

def get_pipeline(employee_id: str) -> Optional[CVPipeline]:
    return pipelines.get(employee_id)

def create_pipeline(employee_record: dict) -> CVPipeline:
    pipeline = CVPipeline(employee_record)
    employee_id = str(employee_record["employee_id"])
    pipelines[employee_id] = pipeline
    return pipeline
