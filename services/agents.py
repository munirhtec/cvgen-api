import json
import re
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from lib.llm import get_llm_response, get_model_for_task
from lib.prompts import load_prompt


# -----------------------
# Schemas
# -----------------------

class LanguageLevel(BaseModel):
    language: str
    level: str


class RelevantProject(BaseModel):
    businessDomain: str
    projectDescription: str
    techStack: List[str]
    roleAndResponsibilities: List[str]
    startDate: Optional[str] = None
    endDate: Optional[str] = None


class ProfessionalSkills(BaseModel):
    coreLanguages: List[str]
    frameworksAndTools: List[str]


class PersonalInformation(BaseModel):
    fullName: str
    position: List[str]
    education: str
    email: EmailStr
    phone: Optional[str] = None


class CVSchema(BaseModel):
    personalInformation: PersonalInformation
    brief: str
    professionalSkills: ProfessionalSkills
    languages: List[LanguageLevel]
    hobbies: List[str]
    relevantProjects: List[RelevantProject]


# -----------------------
# Drafting Agent
# -----------------------

class DraftingAgent:
    def generate(self, employee_record):
        prompts = load_prompt("drafting")

        user_prompt = (
            prompts["user"]
            .replace("{{ employee_record }}", json.dumps(employee_record, indent=2))
        )

        try:
            result = get_llm_response(
                system_prompt=prompts["system"],
                user_prompt=user_prompt,
                temperature=0.2,
                top_p=0.9,
                model=get_model_for_task("cv_drafting"),
                response_model=CVSchema,
            )
            draft = result.parsed.model_dump()
        except Exception as e:
            print(f"Draft generation error: {e}")
            # Fallback empty CV
            draft = CVSchema(
                personalInformation=PersonalInformation(
                    fullName="",
                    position=[],
                    education="",
                    email="example@example.com",
                ),
                brief="",
                professionalSkills=ProfessionalSkills(
                    coreLanguages=[],
                    frameworksAndTools=[],
                ),
                languages=[],
                hobbies=[],
                relevantProjects=[],
            ).model_dump()

        return {
            "cv": draft,
            "feedbackHistory": [],
            "lastFeedback": "",
            "feedback": [],
        }


# -----------------------
# Review Agent
# -----------------------

class ReviewAgent:
    def review(self, draft, feedback=None):
        """
        Review and improve CV draft.
        
        Args:
            draft: CV draft to review
            feedback: Optional user feedback. If None, performs automated fact-checking.
        """
        prompts = load_prompt("review")
        
        # If no feedback provided, use automated fact-checking message
        if feedback is None:
            feedback = "Perform automated fact-checking: verify all information against source data and remove any hallucinations."

        user_prompt = (
            prompts["user"]
            .replace("{{ cv_draft }}", json.dumps(draft["cv"], indent=2))
            .replace("{{ feedback }}", feedback if isinstance(feedback, str) else json.dumps(feedback, indent=2))
        )

        try:
            result = get_llm_response(
                system_prompt=prompts["system"],
                user_prompt=user_prompt,
                temperature=0.2,
                top_p=0.9,
                model=get_model_for_task("cv_review"),
                response_model=CVSchema,
            )
            draft["cv"] = result.parsed.model_dump()
        except Exception as e:
            print(f"Review error: {e}")

        return draft


# -----------------------
# Refinement Agent
# -----------------------

class RefinementAgent:
    def refine(self, draft, employee_record):
        prompts = load_prompt("refinement")

        user_prompt = (
            prompts["user"]
            .replace("{{ employee_record }}", json.dumps(employee_record, indent=2))
            .replace("{{ current_cv }}", json.dumps(draft["cv"], indent=2))
            .replace("{{ feedback }}", json.dumps(draft.get("feedback", []), indent=2))
        )

        try:
            result = get_llm_response(
                system_prompt=prompts["system"],
                user_prompt=user_prompt,
                temperature=0.3,
                top_p=0.9,
                model=get_model_for_task("cv_refinement"),
                response_model=CVSchema,
            )
            draft["cv"] = result.parsed.model_dump()
        except Exception as e:
            print(f"Refinement error: {e}")

        draft["lastFeedback"] = (
            draft.get("feedback", [])[-1]
            if draft.get("feedback")
            else draft.get("lastFeedback", "")
        )

        return draft
