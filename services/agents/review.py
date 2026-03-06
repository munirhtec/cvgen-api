import json
from lib.llm import get_llm_response, get_model_for_task
from lib.prompts import load_prompt
from models.cv import CVSchema
from models.feedback import LLMFeedback

class ReviewAgent:
    def _generate_llm_feedback(self, employee_record: dict, cv_draft: dict) -> str:
        """
        Ask the LLM to critique the CV draft against the source record.
        Returns a plain-text feedback string to feed into the review pass.
        """
        prompts = load_prompt("self_critique")
        user_prompt = (
            prompts["user"]
            .replace("{{ employee_record }}", json.dumps(employee_record, indent=2))
            .replace("{{ cv_draft }}", json.dumps(cv_draft, indent=2))
        )
        
        try:
            result = get_llm_response(
                system_prompt=prompts["system"],
                user_prompt=user_prompt,
                temperature=0.1,
                model=get_model_for_task("cv_review"),
                response_model=LLMFeedback,
            )
            fb = result.parsed
            lines = ["=== LLM Self-Critique ==="]
            if fb.issues:
                lines.append("Issues found:")
                lines.extend(f"  - {i}" for i in fb.issues)
            if fb.suggestions:
                lines.append("Suggestions:")
                lines.extend(f"  - {s}" for s in fb.suggestions)
            lines.append(f"Summary: {fb.summary}")
            return "\n".join(lines)
        except Exception as e:
            print(f"LLM self-feedback generation failed: {e}")
            return (
                "Perform automated fact-checking: verify all information against "
                "the source employee record and remove any hallucinations."
            )

    def review(self, draft, employee_record: dict | None = None, feedback=None, log_cb=None):
        if log_cb: log_cb("🔍 [ReviewAgent] Starting review process...")
        """
        Review and improve CV draft.
        """
        prompts = load_prompt("review")

        # Resolve feedback: prefer explicit user feedback, else LLM self-critique.
        if feedback is None:
            if employee_record:
                feedback = self._generate_llm_feedback(employee_record, draft["cv"])
            else:
                feedback = (
                    "Perform automated fact-checking: verify all information against "
                    "source data and remove any hallucinations."
                )

        record_json = json.dumps(employee_record or {}, indent=2)

        user_prompt = (
            prompts["user"]
            .replace("{{ employee_record }}", record_json)
            .replace("{{ cv_draft }}", json.dumps(draft["cv"], indent=2))
            .replace(
                "{{ feedback }}",
                feedback if isinstance(feedback, str) else json.dumps(feedback, indent=2),
            )
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
            if log_cb: log_cb("✅ [ReviewAgent] Review process complete.")
        except Exception as e:
            msg = f"Review error: {e}"
            print(msg)
            if log_cb: log_cb(f"❌ [ReviewAgent] {msg}")

        return draft
