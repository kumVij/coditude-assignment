import io
import re

from docx import Document
from pypdf import PdfReader

SKILLS = {
    "python", "java", "javascript", "typescript", "react", "node.js", "fastapi", "django",
    "sql", "postgresql", "mongodb", "aws", "azure", "gcp", "docker", "kubernetes",
    "machine learning", "nlp", "llm", "pytorch", "tensorflow", "spring boot", "graphql",
}


def extract_resume(filename: str, content: bytes) -> tuple[str, list[str], float | None]:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
    elif lower.endswith(".docx"):
        document = Document(io.BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    else:
        raise ValueError("Only PDF and DOCX resumes are supported")
    normalized = text.lower()
    skills = sorted(skill for skill in SKILLS if skill in normalized)
    experience = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs)", normalized)
    return text, skills, float(experience.group(1)) if experience else None