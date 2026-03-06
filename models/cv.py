from typing import List, Optional
from pydantic import BaseModel, EmailStr

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
