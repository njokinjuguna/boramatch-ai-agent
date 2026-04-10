import docx
import pdfplumber
import re
import unicodedata
import emoji
from typing import Optional, Dict, List
from fastapi import UploadFile
from keybert import KeyBERT

kw_model = KeyBERT("all-MiniLM-L6-v2")


SKILL_ALIASES = {
    "python": "Python",
    "sql": "SQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "aws": "AWS",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "api": "APIs",
    "apis": "APIs",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "microservices": "Microservices",
    "microservices architecture": "Microservices",
    "git": "Git",
    "ci/cd": "CI/CD",
    "api integration": "API Integration",
    "javascript": "JavaScript",
    "devops": "DevOps",
    "backend development": "Backend Development",
    "backend engineering": "Backend Engineering",
    "cloud": "Cloud",
}

GENERIC_SKILL_PHRASES = {
    "experience backend",
    "experience backend developer",
    "backend systems",
    "backend systems skills",
    "backend developer tech",
    "application testing intern",
    "testing intern developer",
    "intern developer digital",
    "skills lpython",
    "lpython lsql",
    "lsql lflask",
    "apis backend",
    "apis backend systems",
    "scalable apis backend",
    "backend architectures collaborated",
    "backend architectures",
    "scalable backend architectures",
    "backend",
    "intern",
    "junior software",
    "experience junior software",
}


# -----------------------------
# Basic extraction helpers
# -----------------------------
def strip_emojis(text: str) -> str:
    return emoji.replace_emoji(text, replace=" ")


def extract_text_from_pdf(file: UploadFile) -> str:
    text = ""
    with pdfplumber.open(file.file) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
    return text


def extract_text_from_docx(file: UploadFile) -> str:
    text = ""
    doc = docx.Document(file.file)
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text


def extract_resume_text(file: UploadFile) -> Optional[str]:
    filename = (file.filename or "").lower()
    if filename.endswith(".pdf"):
        return extract_text_from_pdf(file)
    elif filename.endswith(".docx"):
        return extract_text_from_docx(file)
    return None


def normalize_text(text: str) -> str:
    text = (text or "").strip()
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_text(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    return text.lower()


def clean_phrase(text: str) -> str:
    text = clean_text(text)
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


def normalize_skill_token(text: str) -> str:
    text = clean_phrase(text)

    # Fix OCR/bullet artifacts like lpython, lsql, lrest
    text = re.sub(r"^l(?=[a-z]{2,})", "", text)

    # collapse spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_known_skills_from_text(text: str) -> List[str]:
    cleaned = clean_text(text)
    found = []

    for alias, canonical in SKILL_ALIASES.items():
        pattern = r"\b" + re.escape(alias.lower()) + r"\b"
        if re.search(pattern, cleaned):
            found.append(canonical)

    return list(dict.fromkeys(found))


def clean_skill_candidates(items: List[str]) -> List[str]:
    cleaned = []
    seen = set()

    for item in items:
        value = normalize_skill_token(item)
        if not value:
            continue

        if value in GENERIC_SKILL_PHRASES:
            continue

        if len(value.split()) > 4:
            continue

        if value in SKILL_ALIASES:
            value = SKILL_ALIASES[value]
        else:
            generic_tokens = {
                "experience", "developer", "engineer", "systems",
                "skills", "backend", "application", "testing", "intern"
            }
            tokens = value.split()
            if len(tokens) >= 2 and sum(t in generic_tokens for t in tokens) == len(tokens):
                continue

        key = value.lower()
        if key not in seen:
            seen.add(key)
            cleaned.append(value)

    return cleaned


# -----------------------------
# Contact extraction
# -----------------------------
def extract_contact_info(text: str) -> Dict[str, str]:
    text_no_emoji = strip_emojis(text)
    text_no_emoji = unicodedata.normalize("NFKD", text_no_emoji)

    lines = [line.strip() for line in text_no_emoji.strip().splitlines() if line.strip()]
    normalized_text = re.sub(r"[^\x00-\x7F]+", " ", text_no_emoji)
    normalized_text = re.sub(r"[\u200b-\u200f\u202a-\u202e]", "", normalized_text)
    normalized_text = re.sub(r"\s+", " ", normalized_text)

    email_match = re.search(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", normalized_text)
    phone_match = re.search(r"(\+?\d{1,3}[\s\-]?\(?\d{2,4}\)?[\s\-]?\d{2,5}[\s\-]?\d{2,5})", normalized_text)
    name_capture = re.search(r"(?i)\bname[:\s\-]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", normalized_text)

    full_name = None
    if name_capture:
        full_name = name_capture.group(1).strip()
    else:
        for line in lines[:5]:
            possible = re.match(r"^([A-Z][a-z]+)\s+([A-Z][a-z]+)$", line)
            if possible:
                full_name = f"{possible.group(1)} {possible.group(2)}"
                break

    return {
        "name": full_name if full_name else "Not found",
        "email": email_match.group(0).strip() if email_match else "Not found",
        "phone": phone_match.group(0).strip() if phone_match else "Not found"
    }


# -----------------------------
# Candidate profile extraction
# -----------------------------
def extract_profile_keywords(text: str, top_n: int = 15) -> List[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return []

    keywords = kw_model.extract_keywords(
        cleaned,
        keyphrase_ngram_range=(1, 3),
        stop_words="english",
        top_n=top_n
    )

    raw_phrases = []
    for kw, _score in keywords:
        kw = normalize_skill_token(kw)
        if not kw:
            continue
        if len(kw) < 2:
            continue
        if kw.isdigit():
            continue
        raw_phrases.append(kw)

    known_skills = extract_known_skills_from_text(text)
    keyword_skills = clean_skill_candidates(raw_phrases)

    combined = known_skills + keyword_skills

    deduped = []
    seen = set()
    for skill in combined:
        key = skill.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(skill)

    return deduped[:15]


def estimate_years_experience(text: str) -> int:
    cleaned = clean_text(text)

    explicit = re.search(r"(\d+)\+?\s+years?", cleaned)
    if explicit:
        return int(explicit.group(1))

    years = re.findall(r"\b(19\d{2}|20\d{2})\b", cleaned)
    if not years:
        return 0

    years = sorted({int(y) for y in years})
    if len(years) >= 2:
        return max(0, years[-1] - years[0])

    return 0


def extract_location(text: str) -> Optional[str]:
    raw = text or ""
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

    # Best case: address block
    for i, line in enumerate(top_lines):
        if line.lower() == "address" and i + 2 < len(top_lines):
            candidate = f"{top_lines[i+1]} {top_lines[i+2]}".strip()
            candidate = re.sub(r"\s+", " ", candidate)
            return candidate

    # Header lines with pipe-separated values
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


def extract_work_mode(text: str) -> Optional[str]:
    raw = text or ""
    lowered = raw.lower()

    if re.search(r"\bhybrid\b", lowered):
        return "hybrid"

    if re.search(r"\bremote\b", lowered) or re.search(r"\bwork from home\b", lowered):
        return "remote"

    if re.search(r"\bon[- ]site\b", lowered) or re.search(r"\bonsite\b", lowered) or re.search(r"\bin[- ]office\b", lowered):
        return "onsite"

    return None


def extract_education(text: str) -> List[str]:
    raw = text or ""

    patterns = [
        r"\b(bachelor(?:'s)?(?: degree)?[^\n,.;]*)",
        r"\b(master(?:'s)?(?: degree)?[^\n,.;]*)",
        r"\b(phd[^\n,.;]*)",
        r"\b(diploma[^\n,.;]*)",
        r"\b(degree in[^\n,.;]*)",
        r"\b(bs[ca]?[^\n,.;]*)",
        r"\b(ms[ca]?[^\n,.;]*)",
    ]

    found = []
    for pattern in patterns:
        found.extend(re.findall(pattern, raw, flags=re.IGNORECASE))

    return unique_clean(found)


def extract_certifications(text: str) -> List[str]:
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


def extract_languages(text: str) -> List[str]:
    raw = text or ""

    patterns = [
        r"\bfluent in ([^\n,.;]+)",
        r"\bproficient in ([^\n,.;]+)",
        r"\bnative ([^\n,.;]+)",
        r"\blanguages?\s*:\s*([^\n]+)",
    ]

    found = []
    for pattern in patterns:
        matches = re.findall(pattern, raw, flags=re.IGNORECASE)
        for match in matches:
            parts = re.split(r",|/| and ", match, flags=re.IGNORECASE)
            found.extend(parts)

    return unique_clean(found)


def extract_job_titles(text: str) -> List[str]:
    raw = text or ""
    keywords = extract_profile_keywords(raw, top_n=12)

    title_like = []
    for kw in keywords:
        if any(token.lower() in kw.lower() for token in [
            "engineer", "developer", "teacher", "nurse", "manager", "specialist",
            "analyst", "assistant", "consultant", "coordinator", "recruiter",
            "accountant", "administrator", "designer", "officer"
        ]):
            title_like.append(kw)

    return list(dict.fromkeys(title_like))


def extract_responsibility_evidence(text: str) -> List[str]:
    raw = text or ""
    lines = re.split(r"[\n\r•]+", raw)

    action_cues = (
        "managed", "developed", "built", "led", "taught", "coordinated",
        "designed", "supported", "implemented", "delivered", "maintained",
        "analyzed", "trained", "supervised", "provided", "handled"
    )

    found = []
    for line in lines:
        line_clean = normalize_text(line)
        if any(cue in line_clean.lower() for cue in action_cues) and len(line_clean) > 10:
            found.append(line_clean)

    return found[:15]


def extract_communication_evidence(text: str) -> List[str]:
    raw = text or ""

    patterns = [
        r"\bcommunication skills\b",
        r"\bexcellent communication\b",
        r"\bstrong communication\b",
        r"\binterpersonal skills\b",
        r"\bcustomer service\b",
        r"\bpresentation skills\b",
        r"\bteam collaboration\b",
        r"\bstakeholder management\b",
    ]

    found = []
    lowered = raw.lower()
    for pattern in patterns:
        matches = re.findall(pattern, lowered)
        found.extend(matches)

    return unique_clean(found)


def build_candidate_profile(text: str) -> Dict:
    return {
        "skills": extract_profile_keywords(text, top_n=15),
        "years_experience": estimate_years_experience(text),
        "location": extract_location(text),
        "work_mode": extract_work_mode(text),
        "education": extract_education(text),
        "certifications": extract_certifications(text),
        "languages": extract_languages(text),
        "job_titles": extract_job_titles(text),
        "responsibility_evidence": extract_responsibility_evidence(text),
        "communication_evidence": extract_communication_evidence(text),
    }


# -----------------------------
# Main parser
# -----------------------------
def parse_resume(file: UploadFile) -> Dict[str, str]:
    raw_text = extract_resume_text(file)
    if not raw_text:
        return {
            "text_preview": "",
            "cleaned_text": "",
            "name": "Not found",
            "email": "Not found",
            "phone": "Not found",
            "skills": [],
            "years_experience": 0,
            "location": None,
            "work_mode": None,
            "education": [],
            "certifications": [],
            "languages": [],
            "job_titles": [],
            "responsibility_evidence": [],
            "communication_evidence": [],
        }

    print("\n=== RAW TEXT PREVIEW ===\n")
    print(raw_text[:1000])
    print("\n========================\n")

    contact_info = extract_contact_info(raw_text)
    cleaned = clean_text(raw_text)
    profile = build_candidate_profile(raw_text)

    return {
        "text_preview": raw_text[:1000],
        "cleaned_text": cleaned,
        "name": contact_info["name"],
        "email": contact_info["email"],
        "phone": contact_info["phone"],
        "skills": profile["skills"],
        "years_experience": profile["years_experience"],
        "location": profile["location"],
        "work_mode": profile["work_mode"],
        "education": profile["education"],
        "certifications": profile["certifications"],
        "languages": profile["languages"],
        "job_titles": profile["job_titles"],
        "responsibility_evidence": profile["responsibility_evidence"],
        "communication_evidence": profile["communication_evidence"],
    }