import json
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from your_faiss_module import search  # import your existing FAISS search functions

# 1️⃣ LLM setup
llm = ChatOpenAI(model_name="gpt-4", temperature=0)

# 2️⃣ Extraction agent
extract_prompt = PromptTemplate(
    input_variables=["transcript","slide_deck"],
    template="""
Extract key points from this transcript:
{transcript}

Align with this slide deck reference:
{slide_deck}

Output JSON: {{'slide_title': ['bullet points'], 'needs_review': [...]}}
"""
)

def extract_summary(transcript, slide_deck_text):
    return llm(extract_prompt.format(transcript=transcript, slide_deck=slide_deck_text))

# 3️⃣ RAG retrieval augmentation
def augment_with_rag(summary_json, top_k=3):
    augmented = {}
    for slide, bullets in summary_json.items():
        augmented[slide] = []
        for bullet in bullets:
            sims = search(bullet, top_k)  # your FAISS search
            augmented[slide].append({
                "bullet": bullet,
                "references": sims
            })
    return augmented

# 4️⃣ Refinement agent
refine_prompt = PromptTemplate(
    input_variables=["aggregated_bullets"],
    template="""
Combine the following bullet points into a coherent, persuasive company pitch.
Keep consistent tone and align with slide deck references.
Output final text.
{aggregated_bullets}
"""
)

def refine_pitch(aggregated_bullets):
    return llm(refine_prompt.format(aggregated_bullets=json.dumps(aggregated_bullets)))
