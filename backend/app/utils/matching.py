import json
import pickle
import re
from typing import List, Dict, Tuple, Optional

from sentence_transformers import SentenceTransformer, util
from keybert import KeyBERT

from app.utils.job_parser_llm import parse_job_description_llm
from app.data.resume_db import get_connection, update_application_scores

kw_model = KeyBERT("all-MiniLM-L6-v2")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


# -----------------------------
# Basic helpers
# -----------------------------
def encode_text(text: str):
    return model.encode(text or "", convert_to_tensor=True)


def normalize_text(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def clean_phrase(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r"^[^\w]+|[^\w]+$", "", text)
    return text.strip()


def unique_clean(items: List[str]) -> List[str]:
    seen = set()
    output = []
    for item in items:
        cleaned = clean_phrase(item)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            output.append(cleaned)
    return output


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"[\n\r•]+|(?<=[.!?])\s+", text or "")
    return [p.strip() for p in parts if p and p.strip()]


def phrase_in_text(phrase: str, text: str) -> bool:
    phrase = clean_phrase(phrase)
    text = normalize_text(text)

    if not phrase or not text:
        return False

    pattern = r"\b" + re.escape(phrase) + r"\b"
    return re.search(pattern, text) is not None


# -----------------------------
# Requirement cleaning helpers
# -----------------------------
GENERIC_REQUIREMENT_PHRASES = {
    "requirements",
    "requirement",
    "preferred",
    "preference",
    "responsibilities",
    "responsibility",
    "skills",
    "skill",
    "experience",
    "minimum years",
    "years experience",
    "minimum years experience",
    "required",
    "mandatory",
    "essential",
    "language",
    "languages",
    "good communication",
    "strong experience",
    "related field",
    "computer science or related field",
    "bachelor degree in computer science or related field",
}

SECTION_HEADERS = {
    "requirements": ["requirements", "requirement", "must have", "essential", "mandatory"],
    "preferred": ["preferred", "nice to have", "bonus", "plus", "advantage"],
    "responsibilities": ["responsibilities", "responsibility", "duties", "what you will do", "role overview"],
    "education": ["education", "academic", "degree"],
    "certifications": ["certification", "certifications", "license", "licence", "registration"],
    "languages": ["language", "languages"],
}


def is_noise_phrase(phrase: str) -> bool:
    phrase = clean_phrase(phrase)
    if not phrase:
        return True

    if phrase in GENERIC_REQUIREMENT_PHRASES:
        return True

    filler_tokens = {
        "requirements", "requirement", "preferred", "skills", "skill",
        "experience", "minimum", "years", "language", "languages",
        "responsibilities", "responsibility", "mandatory", "essential",
        "required", "bonus", "plus", "advantage"
    }

    tokens = phrase.split()
    if tokens and all(token in filler_tokens for token in tokens):
        return True

    generic_count = sum(1 for token in tokens if token in filler_tokens)
    if tokens and generic_count / len(tokens) >= 0.7:
        return True

    return False


def clean_extracted_phrases(items: List[str]) -> List[str]:
    cleaned = []
    for item in items:
        item = clean_phrase(item)
        if not item:
            continue
        if len(item) < 3:
            continue
        if is_noise_phrase(item):
            continue
        cleaned.append(item)
    return unique_clean(cleaned)


def split_job_sections(job_description: str) -> Dict[str, str]:
    lines = [line.strip(" -•\t") for line in (job_description or "").splitlines() if line.strip()]

    sections = {
        "general": [],
        "requirements": [],
        "preferred": [],
        "responsibilities": [],
        "education": [],
        "certifications": [],
        "languages": [],
    }

    current_section = "general"

    for line in lines:
        lower = normalize_text(line).rstrip(":")
        matched_section = None

        for section_name, headers in SECTION_HEADERS.items():
            if any(lower == header or lower.startswith(header + ":") for header in headers):
                matched_section = section_name
                break

        if matched_section:
            current_section = matched_section
            continue

        sections[current_section].append(line)

    return {key: "\n".join(value) for key, value in sections.items()}


def extract_bullet_phrases(text: str) -> List[str]:
    if not text:
        return []

    lines = [clean_phrase(line.strip(" -•\t")) for line in text.splitlines() if line.strip()]
    results = []

    for line in lines:
        if not line:
            continue
        if 1 <= len(line.split()) <= 12 and not is_noise_phrase(line):
            results.append(line)

    return unique_clean(results)


def extract_skill_like_phrases(text: str, top_n: int = 12) -> List[str]:
    phrases = extract_keywords(text, top_n=top_n, ngram_range=(1, 3), min_score=0.2)
    return clean_extracted_phrases(phrases)


# -----------------------------
# NLP extraction
# -----------------------------
def extract_keywords(
    text: str,
    top_n: int = 15,
    ngram_range: Tuple[int, int] = (1, 3),
    min_score: float = 0.15,
) -> List[str]:
    text = normalize_text(text)
    if not text:
        return []

    keywords = kw_model.extract_keywords(
        text,
        keyphrase_ngram_range=ngram_range,
        stop_words="english",
        top_n=top_n,
    )

    phrases = []
    for kw, score in keywords:
        kw = clean_phrase(kw)
        if not kw:
            continue
        if len(kw) < 2:
            continue
        if kw.isdigit():
            continue
        if score < min_score:
            continue
        phrases.append(kw)

    return clean_extracted_phrases(phrases)


# -----------------------------
# Job requirement extraction
# -----------------------------
def extract_min_years_from_job(job_description: str) -> Optional[int]:
    text = normalize_text(job_description)

    patterns = [
        r"minimum\s+of\s+(\d+)\s+years?",
        r"minimum\s+(\d+)\s+years?",
        r"at\s+least\s+(\d+)\s+years?",
        r"(\d+)\+?\s+years?\s+of\s+experience",
        r"(\d+)\+?\s+years?",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def extract_location_from_job(job_description: str) -> Optional[str]:
    text = job_description or ""

    patterns = [
        r"location\s*:\s*([^\n,.;]+)",
        r"job location\s*:\s*([^\n,.;]+)",
        r"based in\s+([^\n,.;]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = clean_phrase(match.group(1))
            if value:
                return value

    if re.search(r"\bremote\b", text, flags=re.IGNORECASE):
        return "remote"

    return None


def extract_work_mode_from_text(text: str) -> Optional[str]:
    raw = text or ""
    lowered = raw.lower()

    if re.search(r"\bhybrid\b", lowered):
        return "hybrid"

    if re.search(r"\bremote\b", lowered) or re.search(r"\bwork from home\b", lowered):
        return "remote"

    if re.search(r"\bon[- ]site\b", lowered) or re.search(r"\bonsite\b", lowered) or re.search(r"\bin[- ]office\b", lowered):
        return "onsite"

    return None


def extract_education_from_text(text: str) -> List[str]:
    raw = text or ""
    patterns = [
        r"\b(bachelor(?:'s)?(?: degree)?[^\n,.;]*)",
        r"\b(master(?:'s)?(?: degree)?[^\n,.;]*)",
        r"\b(phd[^\n,.;]*)",
        r"\b(diploma[^\n,.;]*)",
        r"\b(degree in[^\n,.;]*)",
    ]

    found = []
    for pattern in patterns:
        found.extend(re.findall(pattern, raw, flags=re.IGNORECASE))
    return unique_clean(found)


def extract_certifications_from_text(text: str) -> List[str]:
    raw = text or ""
    patterns = [
        r"\b(certification in[^\n,.;]*)",
        r"\b(certified [^\n,.;]*)",
        r"\b(license[^\n,.;]*)",
        r"\b(licence[^\n,.;]*)",
        r"\b(registration[^\n,.;]*)",
        r"\b([A-Z]{2,10}\s+certification)\b",
        r"\b([A-Z]{2,10}\s+certified)\b",
    ]

    found = []
    for pattern in patterns:
        found.extend(re.findall(pattern, raw, flags=re.IGNORECASE))
    return unique_clean(found)


def extract_languages_from_text(text: str) -> List[str]:
    raw = text or ""

    patterns = [
        r"\bfluent in ([^\n,.;]+)",
        r"\bproficient in ([^\n,.;]+)",
        r"\bnative ([^\n,.;]+)",
        r"\blanguages?\s*:\s*([^\n]+)",
        r"\benglish required\b",
        r"\bitalian required\b",
        r"\bfrench required\b",
        r"\bgerman required\b",
        r"\bspanish required\b",
    ]

    found = []
    for pattern in patterns:
        matches = re.findall(pattern, raw, flags=re.IGNORECASE)
        if isinstance(matches, list):
            for match in matches:
                if isinstance(match, str):
                    parts = re.split(r",|/| and ", match, flags=re.IGNORECASE)
                    found.extend(parts)

    lowered = raw.lower()
    for language in ["english", "italian", "french", "german", "spanish", "swahili", "arabic"]:
        if f"{language} required" in lowered or f"fluent {language}" in lowered:
            found.append(language)

    return unique_clean(found)


def extract_communication_requirements(text: str) -> List[str]:
    lowered = text.lower() if text else ""
    patterns = [
        r"\bcommunication skills\b",
        r"\bexcellent communication\b",
        r"\bstrong communication\b",
        r"\binterpersonal skills\b",
        r"\bcustomer service\b",
        r"\bpresentation skills\b",
        r"\bstakeholder management\b",
        r"\bteam collaboration\b",
    ]

    found = []
    for pattern in patterns:
        found.extend(re.findall(pattern, lowered))
    return unique_clean(found)


def extract_responsibility_phrases(text: str) -> List[str]:
    sentences = split_sentences(text)
    action_cues = (
        "manage", "develop", "build", "lead", "teach", "coordinate", "design",
        "support", "implement", "deliver", "maintain", "analyze", "train",
        "supervise", "provide", "handle", "responsible for", "collaborate", "write"
    )

    responsibility_sentences = []
    for sentence in sentences:
        lowered = normalize_text(sentence)
        if any(cue in lowered for cue in action_cues):
            responsibility_sentences.append(sentence)

    line_based = extract_bullet_phrases("\n".join(responsibility_sentences))
    if line_based:
        return line_based[:8]

    if not responsibility_sentences:
        return []

    return extract_skill_like_phrases(" ".join(responsibility_sentences), top_n=8)


def extract_job_requirements_rule_based(job_description: str) -> Dict:
    sections = split_job_sections(job_description)

    general_text = sections["general"]
    requirements_text = sections["requirements"]
    preferred_text = sections["preferred"]
    responsibilities_text = sections["responsibilities"]
    education_text = sections["education"]
    certifications_text = sections["certifications"]
    languages_text = sections["languages"]

    required_phrases = extract_bullet_phrases(requirements_text)
    if not required_phrases:
        source_text = requirements_text if requirements_text else general_text
        required_phrases = extract_skill_like_phrases(source_text, top_n=8)

    preferred_phrases = extract_bullet_phrases(preferred_text)
    if not preferred_phrases and preferred_text:
        preferred_phrases = extract_skill_like_phrases(preferred_text, top_n=5)

    preferred_phrases = [p for p in preferred_phrases if p not in required_phrases]

    responsibility_phrases = extract_responsibility_phrases(
        responsibilities_text if responsibilities_text else job_description
    )

    education_requirements = extract_education_from_text(
        education_text if education_text else job_description
    )

    certification_requirements = extract_certifications_from_text(
        certifications_text if certifications_text else job_description
    )

    language_requirements = extract_languages_from_text(
        languages_text if languages_text else job_description
    )

    communication_requirements = extract_communication_requirements(
        f"{requirements_text}\n{preferred_text}\n{responsibilities_text}\n{general_text}"
    )

    years_experience = extract_min_years_from_job(job_description)
    location = extract_location_from_job(job_description)
    work_mode = extract_work_mode_from_text(job_description)

    active_dimensions = ["semantic"]

    if required_phrases:
        active_dimensions.append("required_phrases")
    if preferred_phrases:
        active_dimensions.append("preferred_phrases")
    if years_experience is not None:
        active_dimensions.append("years_experience")
    if location:
        active_dimensions.append("location")
    if work_mode:
        active_dimensions.append("work_mode")
    if education_requirements:
        active_dimensions.append("education")
    if certification_requirements:
        active_dimensions.append("certifications")
    if language_requirements:
        active_dimensions.append("languages")
    if responsibility_phrases:
        active_dimensions.append("responsibilities")
    if communication_requirements:
        active_dimensions.append("communication")

    return {
        "required_phrases": required_phrases,
        "preferred_phrases": preferred_phrases,
        "years_experience": years_experience,
        "location": location,
        "work_mode": work_mode,
        "education_requirements": education_requirements,
        "certification_requirements": certification_requirements,
        "language_requirements": language_requirements,
        "responsibility_phrases": responsibility_phrases,
        "communication_requirements": communication_requirements,
        "active_dimensions": active_dimensions,
    }


def extract_job_requirements(job_description: str) -> Dict:
    try:
        requirements = parse_job_description_llm(job_description)
        print("[BoraMatch] Using LLM job parser")
        return requirements
    except Exception as e:
        print(f"[BoraMatch] LLM parser failed, falling back to rule-based parser: {e}")
        return extract_job_requirements_rule_based(job_description)


# -----------------------------
# Resume profile loading
# -----------------------------
def estimate_resume_years(resume_text: str) -> int:
    text = normalize_text(resume_text)

    explicit = re.search(r"(\d+)\+?\s+years?", text)
    if explicit:
        return int(explicit.group(1))

    years = re.findall(r"\b(19\d{2}|20\d{2})\b", text)
    if not years:
        return 0

    years = sorted({int(y) for y in years})
    if len(years) >= 2:
        return max(0, years[-1] - years[0])

    return 0


def extract_location_from_resume(resume_text: str) -> Optional[str]:
    raw = resume_text or ""
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    top_lines = lines[:12]

    labeled_patterns = [
        r"location\s*:\s*([^\n]+)",
        r"address\s*:\s*([^\n]+)",
        r"based in\s+([^\n]+)",
        r"city\s*:\s*([^\n]+)",
        r"residence\s*:\s*([^\n]+)",
    ]

    for pattern in labeled_patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            value = re.sub(r"\s+", " ", value).strip(" ,.-")
            return value or None

    def looks_like_email(value: str) -> bool:
        return re.search(r"[\w\.-]+@[\w\.-]+\.\w+", value) is not None

    def looks_like_phone(value: str) -> bool:
        digits = re.sub(r"\D", "", value)
        return len(digits) >= 7

    def looks_like_person_name(value: str) -> bool:
        tokens = value.strip().split()
        return 1 <= len(tokens) <= 3 and all(token[:1].isupper() for token in tokens if token)

    def looks_like_location(value: str) -> bool:
        value = value.strip()
        if not value:
            return False
        if looks_like_email(value) or looks_like_phone(value):
            return False
        if value.lower() in {"remote", "hybrid", "onsite"}:
            return False
        if looks_like_person_name(value) and "," not in value and "(" not in value:
            return False
        return re.match(r"^[A-Za-zÀ-ÿ'./() -]+(?:,\s*[A-Za-zÀ-ÿ'./() -]+)?$", value) is not None

    # Address block handling
    for i, line in enumerate(top_lines):
        if line.lower() == "address" and i + 2 < len(top_lines):
            candidate = f"{top_lines[i+1]} {top_lines[i+2]}".strip()
            candidate = re.sub(r"\s+", " ", candidate)
            return candidate

    # Header line handling: email | phone | location
    for line in top_lines:
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            for part in parts:
                if looks_like_location(part):
                    return part

    # Standalone location-like lines
    for line in top_lines:
        cleaned = re.sub(r"\s+", " ", line).strip()
        if looks_like_location(cleaned) and ("," in cleaned or "(" in cleaned):
            return cleaned

    if re.search(r"\bremote\b", raw, flags=re.IGNORECASE):
        return "remote"

    return None


def extract_work_mode_from_resume(resume_text: str) -> Optional[str]:
    return extract_work_mode_from_text(resume_text)


def build_resume_profile_fallback(resume_text: str) -> Dict:
    return {
        "skills": extract_keywords(resume_text, top_n=15),
        "years_experience": estimate_resume_years(resume_text),
        "location": extract_location_from_resume(resume_text),
        "work_mode": extract_work_mode_from_resume(resume_text),
        "education": extract_education_from_text(resume_text),
        "certifications": extract_certifications_from_text(resume_text),
        "languages": extract_languages_from_text(resume_text),
        "job_titles": [],
        "responsibility_evidence": extract_responsibility_phrases(resume_text),
        "communication_evidence": extract_communication_requirements(resume_text),
    }


def load_resume_profile(profile_json: Optional[str], resume_text: str) -> Dict:
    if profile_json:
        try:
            profile = json.loads(profile_json)
            if isinstance(profile, dict):
                return {
                    "skills": unique_clean(profile.get("skills", [])),
                    "years_experience": profile.get("years_experience", 0) or 0,
                    "location": clean_phrase(profile.get("location", "")) or None,
                    "work_mode": clean_phrase(profile.get("work_mode", "")) or None,
                    "education": unique_clean(profile.get("education", [])),
                    "certifications": unique_clean(profile.get("certifications", [])),
                    "languages": unique_clean(profile.get("languages", [])),
                    "job_titles": unique_clean(profile.get("job_titles", [])),
                    "responsibility_evidence": unique_clean(profile.get("responsibility_evidence", [])),
                    "communication_evidence": unique_clean(profile.get("communication_evidence", [])),
                }
        except Exception:
            pass

    return build_resume_profile_fallback(resume_text)


# -----------------------------
# Matching helpers
# -----------------------------
REQUIREMENT_STOPWORDS = {
    "strong", "good", "excellent", "experience", "with", "in", "of", "and",
    "or", "the", "a", "an", "such", "as", "skills", "skill", "knowledge",
    "minimum", "years", "year", "required", "preferred", "ability"
}


def split_requirement_into_units(requirement: str) -> List[str]:
    requirement = clean_phrase(requirement)
    if not requirement:
        return []

    protected_phrases = [
        "rest apis",
        "sql databases",
        "backend development",
        "communication skills",
        "cloud platforms",
        "computer science",
        "microservices architecture",
    ]

    units = []

    lowered = requirement
    for phrase in protected_phrases:
        if phrase in lowered:
            units.append(phrase)
            lowered = lowered.replace(phrase, " ")

    tokens = re.findall(r"[a-zA-Z0-9\+#\.]+", lowered)
    tokens = [t for t in tokens if t not in REQUIREMENT_STOPWORDS and len(t) > 1]

    units.extend(tokens)
    return unique_clean(units)


def requirement_match_score(requirement: str, profile_values: List[str], resume_text: str) -> Tuple[float, List[str]]:
    units = split_requirement_into_units(requirement)
    if not units:
        return 0.0, []

    matched_units = []
    profile_values = unique_clean(profile_values)
    resume_text = normalize_text(resume_text)

    for unit in units:
        in_profile = any(
            phrase_in_text(unit, value) or phrase_in_text(value, unit)
            for value in profile_values
        )
        in_text = phrase_in_text(unit, resume_text)

        if in_profile or in_text:
            matched_units.append(unit)

    score = len(matched_units) / len(units) if units else 0.0
    return score, matched_units


def match_requirement_list(requirements: List[str], profile_values: List[str], resume_text: str) -> Tuple[float, List[str], List[str]]:
    if not requirements:
        return 1.0, [], []

    matched = []
    missing = []
    per_requirement_scores = []

    for req in unique_clean(requirements):
        req_score, _matched_units = requirement_match_score(req, profile_values, resume_text)

        if req_score >= 0.5:
            matched.append(req)
        else:
            missing.append(req)

        per_requirement_scores.append(req_score)

    score = sum(per_requirement_scores) / len(per_requirement_scores) if per_requirement_scores else 0.0
    return score, matched, missing


def calculate_experience_score(required_years: Optional[int], resume_years: int) -> float:
    if required_years is None:
        return 1.0
    if resume_years <= 0:
        return 0.0
    return min(resume_years / required_years, 1.0)


def calculate_location_score(job_location: Optional[str], resume_location: Optional[str]) -> float:
    if not job_location:
        return 1.0
    if not resume_location:
        return 0.0

    job_location = clean_phrase(job_location)
    resume_location = clean_phrase(resume_location)

    if job_location == "remote":
        return 1.0
    if job_location == resume_location:
        return 1.0
    if job_location in resume_location or resume_location in job_location:
        return 0.8
    return 0.0


def calculate_work_mode_score(job_work_mode: Optional[str], resume_work_mode: Optional[str]) -> float:
    if not job_work_mode:
        return 1.0
    if not resume_work_mode:
        return 0.0

    job_work_mode = clean_phrase(job_work_mode)
    resume_work_mode = clean_phrase(resume_work_mode)

    if job_work_mode == resume_work_mode:
        return 1.0
    return 0.0


def responsibility_score(requirement_phrases: List[str], evidence_phrases: List[str], resume_text: str) -> Tuple[float, List[str], List[str]]:
    return match_requirement_list(requirement_phrases, evidence_phrases, resume_text)


def communication_score(requirements: List[str], evidence: List[str], resume_text: str) -> Tuple[float, List[str], List[str]]:
    return match_requirement_list(requirements, evidence, resume_text)


def compute_dynamic_final_score(score_map: Dict[str, float], active_dimensions: List[str]) -> float:
    weight_plan = {
        "semantic": 0.28,
        "required_phrases": 0.22,
        "preferred_phrases": 0.08,
        "years_experience": 0.08,
        "location": 0.05,
        "work_mode": 0.05,
        "education": 0.05,
        "certifications": 0.07,
        "languages": 0.05,
        "responsibilities": 0.05,
        "communication": 0.02,
    }

    active_weights = {k: weight_plan[k] for k in active_dimensions if k in weight_plan}
    total_weight = sum(active_weights.values())

    if total_weight <= 0:
        return 0.0

    weighted_sum = sum(score_map.get(k, 0.0) * weight for k, weight in active_weights.items())
    return weighted_sum / total_weight


def get_confidence_label(score: float) -> str:
    if score >= 0.80:
        return "Strong match"
    if score >= 0.60:
        return "Medium match"
    return "Low match"


def get_shortlist_status(score: float) -> str:
    if score >= 0.80:
        return "Shortlisted"
    if score >= 0.60:
        return "Review"
    return "Not shortlisted"


def build_explanation(
    requirements: Dict,
    matched_required: List[str],
    missing_required: List[str],
    matched_preferred: List[str],
    matched_education: List[str],
    matched_certifications: List[str],
    matched_languages: List[str],
    matched_responsibilities: List[str],
    matched_communication: List[str],
    semantic_score: float,
    resume_profile: Dict,
) -> str:
    parts = []

    if matched_required:
        parts.append(f"Matched core requirements: {', '.join(matched_required)}")

    if missing_required:
        parts.append(f"Missing core requirements: {', '.join(missing_required)}")

    if matched_preferred:
        parts.append(f"Matched preferred requirements: {', '.join(matched_preferred)}")

    if matched_education:
        parts.append(f"Matched education requirements: {', '.join(matched_education)}")

    if matched_certifications:
        parts.append(f"Matched certifications/licenses: {', '.join(matched_certifications)}")

    if matched_languages:
        parts.append(f"Matched language requirements: {', '.join(matched_languages)}")

    if matched_responsibilities:
        parts.append(f"Matched responsibility evidence: {', '.join(matched_responsibilities[:5])}")

    if matched_communication:
        parts.append(f"Matched communication evidence: {', '.join(matched_communication)}")

    if requirements.get("years_experience") is not None:
        parts.append(
            f"Estimated experience: {resume_profile.get('years_experience', 0)} years against requirement of {requirements['years_experience']} years"
        )

    if requirements.get("location"):
        parts.append(
            f"Location check: candidate='{resume_profile.get('location') or 'unknown'}', job='{requirements['location']}'"
        )

    if requirements.get("work_mode"):
        parts.append(
            f"Work mode check: candidate='{resume_profile.get('work_mode') or 'unknown'}', job='{requirements['work_mode']}'"
        )

    parts.append(f"Semantic similarity score: {round(semantic_score, 4)}")

    return ". ".join(parts) + "."


# -----------------------------
# Main matcher
# -----------------------------
def match_resumes(
    job_description: str,
    job_id: str,
    top_k: int = 5,
    min_score: float = 0.30,
) -> Dict:
    job_description = job_description or ""
    job_embedding = encode_text(job_description)

    requirements = extract_job_requirements(job_description)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            a.application_id,
            a.job_id,
            a.resume_file_id,
            a.resume_filename,
            a.application_status,
            c.candidate_id,
            c.name AS candidate_name,
            c.email AS candidate_email,
            c.phone AS candidate_phone,
            c.latest_resume_text,
            c.latest_embedding,
            c.profile_json
        FROM applications a
        JOIN candidates c ON a.candidate_id = c.candidate_id
        WHERE a.job_id = ?
    """, (job_id,))
    resumes = cursor.fetchall()
    conn.close()

    seen_candidates = set()
    ranked_candidates = []

    for row in resumes:
        application_id = row["application_id"]
        file_id = row["resume_file_id"]
        filename = row["resume_filename"]
        resume_text = row["latest_resume_text"]
        embedding_blob = row["latest_embedding"]
        candidate_id = row["candidate_id"]
        candidate_name = row["candidate_name"]
        candidate_email = row["candidate_email"]
        candidate_phone = row["candidate_phone"]
        profile_json = row["profile_json"]

        if candidate_id in seen_candidates:
            continue
        seen_candidates.add(candidate_id)

        if not resume_text or not embedding_blob:
            continue

        resume_profile = load_resume_profile(profile_json, resume_text)
        print(
            f"[DEBUG] {candidate_name} | location={resume_profile.get('location')} | work_mode={resume_profile.get('work_mode')}"
        )
        resume_embedding = pickle.loads(embedding_blob)
        semantic_score_value = float(util.cos_sim(job_embedding, resume_embedding))

        required_score, matched_required, missing_required = match_requirement_list(
            requirements["required_phrases"],
            resume_profile.get("skills", []),
            resume_text,
        )

        preferred_score, matched_preferred, missing_preferred = match_requirement_list(
            requirements["preferred_phrases"],
            resume_profile.get("skills", []),
            resume_text,
        )

        education_score_value, matched_education, missing_education = match_requirement_list(
            requirements["education_requirements"],
            resume_profile.get("education", []),
            resume_text,
        )

        certification_score_value, matched_certifications, missing_certifications = match_requirement_list(
            requirements["certification_requirements"],
            resume_profile.get("certifications", []),
            resume_text,
        )

        language_score_value, matched_languages, missing_languages = match_requirement_list(
            requirements["language_requirements"],
            resume_profile.get("languages", []),
            resume_text,
        )

        responsibility_score_value, matched_responsibilities, missing_responsibilities = responsibility_score(
            requirements["responsibility_phrases"],
            resume_profile.get("responsibility_evidence", []),
            resume_text,
        )

        communication_score_value, matched_communication, missing_communication = communication_score(
            requirements["communication_requirements"],
            resume_profile.get("communication_evidence", []),
            resume_text,
        )

        experience_score_value = calculate_experience_score(
            requirements["years_experience"],
            int(resume_profile.get("years_experience", 0) or 0),
        )

        location_score_value = calculate_location_score(
            requirements["location"],
            resume_profile.get("location"),
        )

        work_mode_score_value = calculate_work_mode_score(
            requirements["work_mode"],
            resume_profile.get("work_mode"),
        )

        score_map = {
            "semantic": semantic_score_value,
            "required_phrases": required_score,
            "preferred_phrases": preferred_score,
            "years_experience": experience_score_value,
            "location": location_score_value,
            "work_mode": work_mode_score_value,
            "education": education_score_value,
            "certifications": certification_score_value,
            "languages": language_score_value,
            "responsibilities": responsibility_score_value,
            "communication": communication_score_value,
        }

        final_score = compute_dynamic_final_score(score_map, requirements["active_dimensions"])
        confidence = get_confidence_label(final_score)
        shortlist_status = get_shortlist_status(final_score)

        update_application_scores(
            application_id=application_id,
            match_score=round(final_score, 4),
            shortlist_status=shortlist_status,
        )

        explanation = build_explanation(
            requirements=requirements,
            matched_required=matched_required,
            missing_required=missing_required,
            matched_preferred=matched_preferred,
            matched_education=matched_education,
            matched_certifications=matched_certifications,
            matched_languages=matched_languages,
            matched_responsibilities=matched_responsibilities,
            matched_communication=matched_communication,
            semantic_score=semantic_score_value,
            resume_profile=resume_profile,
        )

        if final_score >= min_score:
            ranked_candidates.append({
                "application": {
                    "application_id": application_id,
                    "job_id": job_id,
                    "status": row["application_status"],
                },
                "candidate": {
                    "candidate_id": candidate_id,
                    "file_id": file_id,
                    "filename": filename,
                    "name": candidate_name,
                    "email": candidate_email,
                    "phone": candidate_phone,
                },
                "profile": resume_profile,
                "scores": {
                    "final_score": round(final_score, 4),
                    "semantic_score": round(semantic_score_value, 4),
                    "required_score": round(required_score, 4),
                    "preferred_score": round(preferred_score, 4),
                    "experience_score": round(experience_score_value, 4),
                    "location_score": round(location_score_value, 4),
                    "work_mode_score": round(work_mode_score_value, 4),
                    "education_score": round(education_score_value, 4),
                    "certification_score": round(certification_score_value, 4),
                    "language_score": round(language_score_value, 4),
                    "responsibility_score": round(responsibility_score_value, 4),
                    "communication_score": round(communication_score_value, 4),
                },
                "match_analysis": {
                    "confidence": confidence,
                    "shortlist_status": shortlist_status,
                    "matched_required": matched_required,
                    "missing_required": missing_required,
                    "matched_preferred": matched_preferred,
                    "missing_preferred": missing_preferred,
                    "matched_education": matched_education,
                    "missing_education": missing_education,
                    "matched_certifications": matched_certifications,
                    "missing_certifications": missing_certifications,
                    "matched_languages": matched_languages,
                    "missing_languages": missing_languages,
                    "matched_responsibilities": matched_responsibilities,
                    "missing_responsibilities": missing_responsibilities,
                    "matched_communication": matched_communication,
                    "missing_communication": missing_communication,
                },
                "explanation": explanation,
                "snippet": (resume_text or "")[:300],
            })

    ranked_candidates = sorted(
        ranked_candidates,
        key=lambda item: item["scores"]["final_score"],
        reverse=True
    )[:top_k]

    return {
        "job_requirements": requirements,
        "matches_found": len(ranked_candidates),
        "results": ranked_candidates,
    }