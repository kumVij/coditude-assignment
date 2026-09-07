"""
Turns free-text job description into simple search criteria for the people
search API: candidate job-title keywords + skill keywords.

This is a lightweight heuristic (keyword/skill dictionary matching) so the
assignment has no hard dependency on an LLM API key. Swapping this for an
LLM-based JD parser (e.g. Claude via the Anthropic API) is a drop-in
replacement — see README "Next steps".
"""
import re
from app.services.llm import generate_json

COMMON_TITLE_WORDS = [
    "engineer", "developer", "manager", "director", "designer", "analyst",
    "scientist", "architect", "consultant", "lead", "recruiter", "specialist",
    "product manager", "software engineer", "data scientist", "sales", "marketing",
    "devops", "sre", "qa", "full stack", "backend", "frontend", "ml engineer",
]

SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "react", "next.js", "node.js",
    "fastapi", "django", "flask", "aws", "gcp", "azure", "docker", "kubernetes",
    "sql", "postgresql", "mongodb", "machine learning", "nlp", "llm", "pytorch",
    "tensorflow", "go", "golang", "rust", "c++", "spring boot", "graphql",
    "terraform", "ci/cd", "microservices", "figma", "salesforce", "seo", "b2b sales",
]


def parse_job_description(title: str, description: str) -> dict:
    generated = generate_json(
        f"Parse this recruiting JD into JSON with arrays titles and skills. Include normalized, specific "
        f"search terms only. Title: {title}. Description: {description}. Return JSON only."
    )
    if generated and isinstance(generated.get("titles"), list) and isinstance(generated.get("skills"), list):
        return {"titles": generated["titles"][:8], "skills": generated["skills"][:12]}
    text = f"{title}\n{description}".lower()

    titles_found = sorted({t for t in COMMON_TITLE_WORDS if t in text})
    skills_found = sorted({s for s in SKILL_KEYWORDS if s in text})

    # Always include the literal job title as a title keyword too.
    clean_title = re.sub(r"[^a-zA-Z0-9 ]", "", title).strip().lower()
    if clean_title and clean_title not in titles_found:
        titles_found = [clean_title] + titles_found

    return {"titles": titles_found[:8], "skills": skills_found[:12]}
