import re

# Simple pattern-based check for obviously dangerous/harmful weapon creation instructions
UNSAFE_PATTERNS = [
    # Requests to create or construct weapons
    r"\b(how\s+(to|do\s+i)|can\s+i|help\s+me\s+to)?\s*(make|build|construct|manufacture|assemble|create)\s+(a\s+)?(homemade\s+|diy\s+)?(gun|firearm|pistol|rifle|zip\s+gun|bomb|silencer|suppressor|explosive|receiver)\b",

    # Specific dangerous weapon-construction requests
    r"\b(homemade|diy)\s+(zip\s+gun|silencer|muffler|baffle|firearm|weapon)\b",

    # 3D-printed weapon components
    r"\b3d\s*print(ing)?\s+(a\s+)?(receiver|frame|gun|firearm|lower|upper)\b",

    # Automatic weapon conversion
    r"\bconvert.*\b(to\s+)?(full\s+auto|fully\s+automatic|machine\s+gun)\b",

    # Explosive or ammunition construction
    r"\b(diy|homemade)\s+(gunpowder|explosive|thermite|ammunition|bullet)\b",

    # Weapon modification requests
    r"\bmodify(ing)?\s+(a\s+)?(gun|firearm|weapon)\s+to\b"
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
5. **Tone & Length**: Your answer MUST be extremely simple and properly formatted. Limit your response to 1 or 2 sentences maximum. Do not write a whole paragraph. Be objective, clear, and educational.

Retrieved Context:
---
{context}
---
"""
