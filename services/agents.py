import json
import re

from lib.llm import get_llm_response

class DraftingAgent:
    def generate(self, employee_record):
        prompt = f"""
        You are an expert CV writer. Create a JSON CV draft from the employee record:
        {employee_record}
        Return a JSON object with keys: full_name, current_role, work_experience, skills, endorsements, business_context
        """
        result = get_llm_response(prompt)
        
        try:
            content = result.choices[0].message.content
        except Exception:
            content = str(result)

        content = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.DOTALL)

        json_match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                draft = json.loads(json_str)
            except json.JSONDecodeError:
                draft = {}
        else:
            draft = {}

        return {"cv": draft, "feedback": []}


class ReviewAgent:
    def review(self, draft):
        prompt = f"""
        You are a CV reviewer. Review this CV draft:
        {draft['cv']}
        Highlight inconsistencies, missing fields, and low-confidence areas.
        Return a JSON list of feedback items: [{"field":..., "issue":...}]
        """
        result = get_llm_response(prompt)
        try:
            feedback = json.loads(result.choices[0].message["content"])
        except:
            feedback = []
        draft["feedback"] = feedback
        return draft


class RefinementAgent:
    def refine(self, draft, employee_record):
        """
        Improve the CV draft based on the feedback and employee record.
        Feedback is preserved and never erased.
        """
        prompt = f"""
        You are a CV refinement assistant. 
        Improve the CV draft based on the feedback below and the employee record.
        
        CV Draft: {draft['cv']}
        Feedback: {draft.get('feedback', [])}
        Employee Record: {employee_record}
        
        Return a JSON object representing the updated CV (full_name, current_role, work_experience, skills, endorsements, business_context).
        """
        result = get_llm_response(prompt)

        # Extract JSON from LLM response
        try:
            content = result.choices[0].message.content
            content = re.sub(r"^```json\s*|\s*```$", "", content.strip(), flags=re.DOTALL)
            json_match = re.search(r"\{.*\}", content, flags=re.DOTALL)
            if json_match:
                draft["cv"] = json.loads(json_match.group(0))
        except Exception:
            draft["cv"] = draft.get("cv", {})

        # DO NOT erase feedback
        if "feedback" not in draft:
            draft["feedback"] = []

        return draft

