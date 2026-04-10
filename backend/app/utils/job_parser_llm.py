import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEYy"))


JOB_REQUIREMENTS_SCHEMA_EXAMPLE = {
    "required_phrases": [],
    "preferred_phrases": [],
    "years_experience": None,
    "location": None,
    "work_mode": None,
    "education_requirements": [],
    "certification_requirements": [],
    "language_requirements": [],
    "responsibility_phrases": [],
    "communication_requirements": [],
    "active_dimensions": []
}


def _clean_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned = []
    seen = set()

    for item in values:
        if not isinstance(item, str):
            continue
        value = item.strip().lower()
        if not value:
            continue
        if value not in seen:
            seen.add(value)
            cleaned.append(value)

    return cleaned


def _normalize_output(data: Dict[str, Any]) -> Dict[str, Any]:
    result = {
        "required_phrases": _clean_list(data.get("required_phrases")),
        "preferred_phrases": _clean_list(data.get("preferred_phrases")),
        "years_experience": data.get("years_experience"),
        "location": (data.get("location") or None),
        "work_mode": (data.get("work_mode") or None),
        "education_requirements": _clean_list(data.get("education_requirements")),
        "certification_requirements": _clean_list(data.get("certification_requirements")),
        "language_requirements": _clean_list(data.get("language_requirements")),
        "responsibility_phrases": _clean_list(data.get("responsibility_phrases")),
        "communication_requirements": _clean_list(data.get("communication_requirements")),
        "active_dimensions": []
    }

    if not isinstance(result["years_experience"], int):
        result["years_experience"] = None

    if isinstance(result["location"], str):
        result["location"] = result["location"].strip().lower() or None

    if isinstance(result["work_mode"], str):
        result["work_mode"] = result["work_mode"].strip().lower() or None

    active_dimensions = ["semantic"]

    if result["required_phrases"]:
        active_dimensions.append("required_phrases")
    if result["preferred_phrases"]:
        active_dimensions.append("preferred_phrases")
    if result["years_experience"] is not None:
        active_dimensions.append("years_experience")
    if result["location"]:
        active_dimensions.append("location")
    if result["work_mode"]:
        active_dimensions.append("work_mode")
    if result["education_requirements"]:
        active_dimensions.append("education")
    if result["certification_requirements"]:
        active_dimensions.append("certifications")
    if result["language_requirements"]:
        active_dimensions.append("languages")
    if result["responsibility_phrases"]:
        active_dimensions.append("responsibilities")
    if result["communication_requirements"]:
        active_dimensions.append("communication")

    result["active_dimensions"] = active_dimensions
    return result


def parse_job_description_llm(job_description: str) -> Dict[str, Any]:
    prompt = f"""
You are an expert recruitment requirements parser.

Your task:
Extract structured hiring requirements from the job description.

Rules:
1. Return ONLY valid JSON.
2. Do not include markdown, code fences, comments, or explanations.
3. Keep phrases concise and recruiter-meaningful.
4. Do NOT include junk phrases like:
   - "requirements"
   - "minimum years"
   - "preferred"
   - "responsibilities"
5. Separate core/required requirements from preferred ones.
6. If location contains work mode like "Milan (Hybrid)", split them:
   - location = "milan"
   - work_mode = "hybrid"
7. years_experience must be an integer or null.
8. If a category is absent, return an empty list or null.
9. communication_requirements should include only communication-related requirements.
10. responsibility_phrases should be short action-oriented responsibilities.

Return this exact JSON shape:
{json.dumps(JOB_REQUIREMENTS_SCHEMA_EXAMPLE, indent=2)}

Job description:
{job_description}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You extract structured job requirements as strict JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    content = response.choices[0].message.content or "{}"

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {content}") from exc

    return _normalize_output(parsed)