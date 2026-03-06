from pydantic import BaseModel

class FeedbackRequest(BaseModel):
    employee_id: str
    feedback: str
