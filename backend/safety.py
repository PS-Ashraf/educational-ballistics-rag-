import re

# Simple pattern-based check for obviously dangerous/harmful weapon creation instructions
UNSAFE_PATTERNS = [
    r"how to (make|build|construct|manufacture|assemble) a (gun|firearm|pistol|rifle|bomb|silencer|suppressor|explosive|receiver|zip gun)",
    r"3d print(ing)? a (receiver|frame|gun|firearm|lower|upper)",
    r"convert.*to (full auto|fully automatic|machine gun)",
    r"diy (gunpowder|explosive|thermite|ammunition|bullet)",
    r"modifying a gun to",
    r"homemade (silencer|muffler|baffle|firearm|weapon)"
]

def is_query_safe(query: str) -> bool:
    """
    Checks if a user query requests dangerous operational or construction guidelines.
    """
    query_lower = query.lower()
    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, query_lower):
            return False
    return True

def get_safety_refusal() -> str:
    """
    Standard refusal message for unsafe queries.
    """
    return (
        "I cannot provide instructions or assistance with the construction, modification, "
        "acquisition, or operational use of weapons, ammunition, or explosives. "
        "However, I can discuss the underlying physics of ballistics (such as drag, gravity, or project trajectory), "
        "historical contexts, terminology, and gun safety principles. Let me know if you would "
        "like to explore one of those safe academic topics."
    )

def get_system_prompt(context: str) -> str:
    """
    System prompt that guides the LLM to provide educational, RAG-grounded responses
    while respecting safety boundaries.
    """
    return f"""You are an educational Ballistics Knowledge Assistant. Your primary goal is to provide informational and educational answers about ballistics, physics, history, and safety using the retrieved context provided below.

Rules:
1. **Safety First**: Under no circumstances should you provide blueprints, design files, step-by-step instructions, or guides for building, assembling, or modifying weapons, ammunition, or explosives. If the retrieved context contains such data, ignore it and politely redirect the user to academic concepts.
2. **Grounded Answers**: Base your answers strictly on the retrieved context below. Do not make assumptions, invent citations, or hallucinate sources.
3. **Missing Information**: If the retrieved context does not contain enough information to answer the question, you must reply EXACTLY with: "I don't have any relevant answer for that." Do not say anything else.
4. **No Sources**: Do NOT mention the sources or references in your output. Just provide the answer directly based on the context.
5. **Tone & Length**: Keep your answers EXTREMELY short, concise, and straight to the point. Do not write long paragraphs. A shorter answer is generated much faster, which is critical. Be objective, clear, simple, and educational.

Retrieved Context:
---
{context}
---
"""
