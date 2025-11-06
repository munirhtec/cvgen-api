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
            personalInformation=PersonalInformation(
                fullName="",
                position=[],
                education="",
                email="example@example.com"
            ),
            brief="",
            professionalSkills=ProfessionalSkills(
                coreLanguages=[],
                frameworksAndTools=[]
            ),
            languages=[],
            hobbies=[],
            relevantProjects=[]
        )
        
        prompt = f"""Convert employee data to CV JSON following these rules:

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
        except Exception:
            content = str(result)
        content = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.DOTALL)
        try:
            draft_json = json.loads(content)
            draft = CVSchema(**draft_json)
        except Exception as e:
            print(f"Draft generation error: {e}")
            draft = empty_cv
        return {"cv": draft.model_dump(), "feedback": []}

class ReviewAgent:
    def review(self, draft):
        prompt = f"""Review this CV draft for quality and completeness:

CV DRAFT:
{json.dumps(draft['cv'], indent=2)}

REVIEW CHECKLIST:
1. Is brief compelling and 2-3 sentences? (not generic or empty)
2. Are relevantProjects populated with actual work history?
3. Are skills properly categorized in professionalSkills?
4. Is personalInformation complete (name, position, education, email)?
5. For senior positions, is English language included?
6. Are projectDescriptions clear and specific?
7. Are techStacks identified for each project?

Return JSON array of issues found:
[{{"field": "path.to.field", "issue": "specific problem", "severity": "high|medium|low"}}]

Only report actual problems. If field is intentionally empty (no data available), don't flag it.
Return empty array [] if CV is good."""

        result = get_llm_response(prompt)
        try:
            content = result.choices[0].message.content
            content = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.DOTALL)
            feedback = json.loads(content)
        except Exception as e:
            print(f"Review error: {e}")
            feedback = []
        draft["feedback"] = feedback
        return draft

class RefinementAgent:
    def refine(self, draft, employee_record):
        prompt = f"""Refine CV draft based on feedback and original data:

ORIGINAL DATA:
{employee_record}

CURRENT CV:
{json.dumps(draft['cv'], indent=2)}

FEEDBACK TO ADDRESS:
{json.dumps(draft.get('feedback', []), indent=2)}

REFINEMENT INSTRUCTIONS:
1. Address feedback first (highest priority), most priority has latest entry in the array, one before it if exists has 50% priority, 3rd has 20%
2. Improve clarity and professionalism
3. Return complete CV JSON matching schema

No markdown, no explanations."""

        result = get_llm_response(prompt)
        try:
            content = result.choices[0].message.content
            content = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.DOTALL)
            draft_json = json.loads(content)
            draft["cv"] = CVSchema(**draft_json).model_dump()
            # draft["feedback"] = []  # Clear feedback after refinement
        except Exception as e:
            print(f"Refinement error: {e}")
            draft["cv"] = draft.get("cv", {})
        
        if "feedback" not in draft:
            draft["feedback"] = []
        return draft