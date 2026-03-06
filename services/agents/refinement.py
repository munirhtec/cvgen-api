import json
from lib.llm import get_llm_response, get_model_for_task
from lib.prompts import load_prompt
from models.cv import CVSchema
from services.rag_faiss import search

class RefinementAgent:
    def refine(self, draft, employee_record, log_cb=None):
        msg = f"\n🔄 [RefinementAgent] Starting Context Convergence Loop for: {employee_record.get('full_name', 'Unknown')}"
        print(msg)
        if log_cb: log_cb(msg)
        
        accumulated_context = []
        max_iterations = 2
        
        # Convergence Loop: LLM decides what it needs to know, RAG provides it
        for i in range(max_iterations):
            msg = f"\n📍 [RefinementAgent] Convergence Iteration {i+1}/{max_iterations}"
            print(msg)
            if log_cb: log_cb(msg)
            
            # 1. Ask LLM what it needs to query based on current state
            query_prompts = load_prompt("rag_query_generator")
            query_user_prompt = (
                query_prompts["user"]
                .replace("{{ employee_record }}", json.dumps(employee_record, indent=2))
                .replace("{{ current_cv }}", json.dumps(draft["cv"], indent=2))
            )
            
            msg = f"🤔 [RefinementAgent] LLM is analyzing gaps..."
            print(msg)
            if log_cb: log_cb(msg)
            print("--- [RAG QUERY PROMPT START] ---")
            print(f"SYSTEM PROMPT:\n{query_prompts['system']}")
            print(f"USER PROMPT:\n{query_user_prompt}")
            print("--- [RAG QUERY PROMPT END] ---")
            
            query_response = get_llm_response(
                system_prompt=query_prompts["system"],
                user_prompt=query_user_prompt,
                temperature=0.4,
                model=get_model_for_task("cv_refinement")
            )
            generated_query = query_response.choices[0].message.content.strip()
            msg = f"📤 [RefinementAgent] LLM generated RAG query: '{generated_query}'"
            print(msg)
            if log_cb: log_cb(msg)
            
            # 2. Execute RAG search
            rag_results = search(generated_query, top_k=2)
            
            if rag_results:
                context_snippet = json.dumps([r["record"] for r in rag_results], indent=2)
                accumulated_context.append(context_snippet)
                msg = f"📥 [RefinementAgent] RAG provided {len(rag_results)} records of context."
                print(msg)
                if log_cb: log_cb(msg)
            else:
                msg = f"⚠️ [RefinementAgent] RAG returned no results for this query."
                print(msg)
                if log_cb: log_cb(msg)

        # Final Refinement with gathered context
        msg = f"\n✨ [RefinementAgent] Executing final refinement with accumulated context..."
        print(msg)
        if log_cb: log_cb(msg)
        prompts = load_prompt("refinement")

        user_prompt = (
            prompts["user"]
            .replace("{{ employee_record }}", json.dumps(employee_record, indent=2))
            .replace("{{ current_cv }}", json.dumps(draft["cv"], indent=2))
            .replace("{{ feedback }}", json.dumps(draft.get("feedback", []), indent=2))
        )
        
        if accumulated_context:
            context_header = "\n\n### ADDITIONAL INDUSTRY CONTEXT GATHERED FROM RAG:\n"
            user_prompt += context_header + "\n---\n".join(accumulated_context)

        print("\n✨ [RefinementAgent] Final Refinement Prompt prepared.")
        print("--- [FINAL REFINEMENT PROMPT START] ---")
        print(f"USER PROMPT:\n{user_prompt}")
        print("--- [FINAL REFINEMENT PROMPT END] ---")

        try:
            result = get_llm_response(
                system_prompt=prompts["system"],
                user_prompt=user_prompt,
                temperature=0.2,
                top_p=0.9,
                model=get_model_for_task("cv_refinement"),
                response_model=CVSchema,
            )
            draft["cv"] = result.parsed.model_dump()
            msg = "✅ [RefinementAgent] Final refinement complete."
            print(msg)
            if log_cb: log_cb(msg)
        except Exception as e:
            msg = f"❌ [RefinementAgent] Final refinement error: {e}"
            print(msg)
            if log_cb: log_cb(msg)

        draft["lastFeedback"] = (
            draft.get("feedback", [])[-1]
            if draft.get("feedback")
            else draft.get("lastFeedback", "")
        )

        return draft
