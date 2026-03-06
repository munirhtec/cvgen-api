import json
from lib.llm import get_llm_response, get_model_for_task
from lib.prompts import load_prompt
from models.cv import CVSchema, PersonalInformation, ProfessionalSkills

class DraftingAgent:
    def generate(self, employee_record, log_cb=None):
        if log_cb: log_cb("📝 [DraftingAgent] Generating CV draft...")
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
            if log_cb: log_cb("✅ [DraftingAgent] Draft generation complete.")
        except Exception as e:
            msg = f"Draft generation error: {e}"
            print(msg)
            if log_cb: log_cb("❌ [DraftingAgent] " + msg)
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
