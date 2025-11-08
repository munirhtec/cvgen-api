import json
import re
from typing import List
from pydantic import BaseModel, EmailStr
from lib.llm import get_llm_response

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

class DraftingAgent:
    def generate(self, employee_record):
        empty_cv = CVSchema(
            personalInformation=PersonalInformation(fullName="", position=[], education="", email="example@example.com"),
            brief="",
            professionalSkills=ProfessionalSkills(coreLanguages=[], frameworksAndTools=[]),
            languages=[],
            hobbies=[],
            relevantProjects=[]
        )
        prompt = f"""Convert employee data to CV JSON:

INPUT DATA:
{employee_record}

OUTPUT SCHEMA:
{cv_to_json(empty_cv)}

MAPPING RULES:
1. personalInformation: Map full_name→fullName, current_role→position (as array), education, email
2. brief: Generate 2-3 sentence professional summary from role, experience, and skills. NEVER leave empty.
3. relevantProjects: Combine ALL entries from employment_history + work_experience + projects arrays. Format each as:
   - businessDomain: Infer from role/responsibilities or use "General Software Development"
   - projectDescription: Use responsibilities field
   - techStack: Extract technologies from responsibilities or use empty array
   - roleAndResponsibilities: Convert responsibilities string to bullet points array
   Sort by start_date descending. CRITICAL: Never leave empty if work history exists.
4. professionalSkills: Distribute skills array between coreLanguages (programming languages) and frameworksAndTools (frameworks/tools/technologies)
5. languages: Add {{"language": "English", "level": "Fluent"}} if position contains Senior/Lead/Principal/Staff/Architect/Manager
6. hobbies: Use endorsements array if available, otherwise empty
7. Preserve ALL data from input - never discard information

Return only valid JSON matching the schema. No markdown, no explanations."""

        result = get_llm_response(prompt)
        try:
            content = result.choices[0].message.content
            content = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.DOTALL)
            draft_json = json.loads(content)
            draft = CVSchema(**draft_json).model_dump()
        except Exception as e:
            print(f"Draft generation error: {e}")
            draft = empty_cv.model_dump()

        return {"cv": draft, "feedbackHistory": [], "lastFeedback": "", "feedback": []}

class ReviewAgent:
    def review(self, draft, feedback):
        """Apply feedback directly to the CV draft."""
        prompt = f"""You are a CV expert. 

CV DRAFT:
{json.dumps(draft['cv'], indent=2)}

FEEDBACK:
{feedback}

Your task is to modify the CV based on the feedback. The result should be a refined CV with the feedback fully applied. 
Make sure the feedback is directly incorporated into the CV. You **must** modify the CV draft in line with the feedback provided, not just review it.

Return the updated CV JSON, in the same structure as the original draft.
"""
        result = get_llm_response(prompt)
        try:
            content = result.choices[0].message.content
            content = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.DOTALL)
            draft_json = json.loads(content)
            draft['cv'] = CVSchema(**draft_json).model_dump()
        except Exception as e:
            print(f"Review error: {e}")

        return draft

class RefinementAgent:
    def refine(self, draft, employee_record):
        prompt = f"""Refine CV draft based on feedback:

ORIGINAL DATA:
{employee_record}

CURRENT CV:
{json.dumps(draft['cv'], indent=2)}

FEEDBACK TO ADDRESS:
{json.dumps(draft.get('feedback', []), indent=2)}

Return refined CV JSON matching schema.
Important: Make sure output you give is indeed refined, and never same as input.
"""
        result = get_llm_response(prompt)
        try:
            content = result.choices[0].message.content
            content = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.DOTALL)
            draft_json = json.loads(content)
            draft['cv'] = CVSchema(**draft_json).model_dump()
        except Exception as e:
            print(f"Refinement error: {e}")

        draft['lastFeedback'] = draft.get('feedback', [])[-1] if draft.get('feedback') else draft.get('lastFeedback', "")
        return draft
