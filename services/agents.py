import json
import re
from typing import List
from pydantic import BaseModel, EmailStr

from lib.llm import get_llm_response
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


class ProfessionalSkills(BaseModel):
    coreLanguages: List[str]
    frameworksAndTools: List[str]


class PersonalInformation(BaseModel):
    fullName: str
    position: List[str]
    education: str
    email: EmailStr


class CVSchema(BaseModel):
    personalInformation: PersonalInformation
    brief: str
    professionalSkills: ProfessionalSkills
    languages: List[LanguageLevel]
    hobbies: List[str]
    relevantProjects: List[RelevantProject]


def cv_to_json(cv: CVSchema) -> str:
    return cv.model_dump_json(indent=2)


# -----------------------
# Drafting Agent
# -----------------------

class DraftingAgent:
    def generate(self, employee_record):
        empty_cv = CVSchema(
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
        )

        prompts = load_prompt("drafting")

        user_prompt = (
            prompts["user"]
            .replace("{{ employee_record }}", json.dumps(employee_record, indent=2))
            .replace("{{ output_schema }}", cv_to_json(empty_cv))
        )

        result = get_llm_response(
            system_prompt=prompts["system"],
            user_prompt=user_prompt,
            temperature=0.2,
            top_p=0.9,
        )

        try:
            content = result.choices[0].message.content
            content = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.DOTALL)
            draft_json = json.loads(content)
            draft = CVSchema(**draft_json).model_dump()
        except Exception as e:
            print(f"Draft generation error: {e}")
            draft = empty_cv.model_dump()

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
    def review(self, draft, feedback):
        prompts = load_prompt("review")

        user_prompt = (
            prompts["user"]
            .replace("{{ cv_draft }}", json.dumps(draft["cv"], indent=2))
            .replace("{{ feedback }}", json.dumps(feedback, indent=2))
        )

        result = get_llm_response(
            system_prompt=prompts["system"],
            user_prompt=user_prompt,
            temperature=0.2,
            top_p=0.9,
        )

        try:
            content = result.choices[0].message.content
            content = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.DOTALL)
            draft_json = json.loads(content)
            draft["cv"] = CVSchema(**draft_json).model_dump()
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

        result = get_llm_response(
            system_prompt=prompts["system"],
            user_prompt=user_prompt,
            temperature=0.3,
            top_p=0.9,
        )

        try:
            content = result.choices[0].message.content
            content = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.DOTALL)
            draft_json = json.loads(content)
            draft["cv"] = CVSchema(**draft_json).model_dump()
        except Exception as e:
            print(f"Refinement error: {e}")

        draft["lastFeedback"] = (
            draft.get("feedback", [])[-1]
            if draft.get("feedback")
            else draft.get("lastFeedback", "")
        )

        return draft
