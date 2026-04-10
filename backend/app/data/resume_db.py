import sqlite3
import json
import uuid
from typing import Optional

DB_PATH = "resumes.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_resume_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        # Candidates table: one profile per person
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                candidate_id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT UNIQUE,
                phone TEXT,
                latest_resume_file_id TEXT,
                latest_resume_filename TEXT,
                latest_resume_text TEXT,
                latest_embedding BLOB,
                profile_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Applications table: one application per candidate per job
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                application_id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                job_id TEXT NOT NULL,
                resume_file_id TEXT,
                resume_filename TEXT,
                application_status TEXT DEFAULT 'applied',
                match_score REAL,
                shortlist_status TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(candidate_id, job_id),
                FOREIGN KEY(candidate_id) REFERENCES candidates(candidate_id)
            )
        """)

        conn.commit()


# -----------------------------
# Candidate helpers
# -----------------------------
def get_candidate_by_email(email: Optional[str]):
    if not email or email == "Not found":
        return None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT *
        FROM candidates
        WHERE lower(email) = lower(?)
        LIMIT 1
    """, (email,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_candidate_by_id(candidate_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT *
        FROM candidates
        WHERE candidate_id = ?
        LIMIT 1
    """, (candidate_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def create_candidate(
    name: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    latest_resume_file_id: Optional[str],
    latest_resume_filename: Optional[str],
    latest_resume_text: Optional[str],
    latest_embedding,
    profile: Optional[dict],
):
    candidate_id = f"cand_{uuid.uuid4().hex[:10]}"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO candidates (
            candidate_id, name, email, phone,
            latest_resume_file_id, latest_resume_filename,
            latest_resume_text, latest_embedding, profile_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        candidate_id,
        name,
        email,
        phone,
        latest_resume_file_id,
        latest_resume_filename,
        latest_resume_text,
        latest_embedding,
        json.dumps(profile or {})
    ))
    conn.commit()
    conn.close()

    return candidate_id


def update_candidate(
    candidate_id: str,
    name: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    latest_resume_file_id: Optional[str],
    latest_resume_filename: Optional[str],
    latest_resume_text: Optional[str],
    latest_embedding,
    profile: Optional[dict],
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE candidates
        SET
            name = ?,
            email = ?,
            phone = ?,
            latest_resume_file_id = ?,
            latest_resume_filename = ?,
            latest_resume_text = ?,
            latest_embedding = ?,
            profile_json = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE candidate_id = ?
    """, (
        name,
        email,
        phone,
        latest_resume_file_id,
        latest_resume_filename,
        latest_resume_text,
        latest_embedding,
        json.dumps(profile or {}),
        candidate_id
    ))
    conn.commit()
    conn.close()


def upsert_candidate(
    name: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    latest_resume_file_id: Optional[str],
    latest_resume_filename: Optional[str],
    latest_resume_text: Optional[str],
    latest_embedding,
    profile: Optional[dict],
):
    existing = get_candidate_by_email(email)

    if existing:
        candidate_id = existing["candidate_id"]
        update_candidate(
            candidate_id=candidate_id,
            name=name,
            email=email,
            phone=phone,
            latest_resume_file_id=latest_resume_file_id,
            latest_resume_filename=latest_resume_filename,
            latest_resume_text=latest_resume_text,
            latest_embedding=latest_embedding,
            profile=profile,
        )
        return candidate_id, "updated"

    candidate_id = create_candidate(
        name=name,
        email=email,
        phone=phone,
        latest_resume_file_id=latest_resume_file_id,
        latest_resume_filename=latest_resume_filename,
        latest_resume_text=latest_resume_text,
        latest_embedding=latest_embedding,
        profile=profile,
    )
    return candidate_id, "created"


# -----------------------------
# Application helpers
# -----------------------------
def get_application(candidate_id: str, job_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT *
        FROM applications
        WHERE candidate_id = ? AND job_id = ?
        LIMIT 1
    """, (candidate_id, job_id))
    row = cursor.fetchone()
    conn.close()
    return row


def application_exists(candidate_id: str, job_id: str) -> bool:
    return get_application(candidate_id, job_id) is not None


def create_application(
    candidate_id: str,
    job_id: str,
    resume_file_id: Optional[str],
    resume_filename: Optional[str],
    application_status: str = "applied",
):
    application_id = f"app_{uuid.uuid4().hex[:10]}"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO applications (
            application_id, candidate_id, job_id, resume_file_id, resume_filename, application_status
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        application_id,
        candidate_id,
        job_id,
        resume_file_id,
        resume_filename,
        application_status
    ))
    conn.commit()
    conn.close()

    return application_id


def update_application_scores(
    application_id: str,
    match_score: Optional[float],
    shortlist_status: Optional[str],
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE applications
        SET
            match_score = ?,
            shortlist_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
    """, (match_score, shortlist_status, application_id))
    conn.commit()
    conn.close()


def get_resumes_by_job_id(job_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            a.application_id,
            a.job_id,
            a.application_status,
            a.resume_file_id,
            a.resume_filename,
            a.match_score,
            a.shortlist_status,
            c.candidate_id,
            c.name AS candidate_name,
            c.email AS candidate_email,
            c.phone AS candidate_phone,
            c.latest_resume_text,
            c.profile_json
        FROM applications a
        JOIN candidates c ON a.candidate_id = c.candidate_id
        WHERE a.job_id = ?
        ORDER BY a.created_at DESC
    """, (job_id,))
    rows = cursor.fetchall()
    conn.close()

    resumes = []
    for row in rows:
        resumes.append({
            "application_id": row["application_id"],
            "job_id": row["job_id"],
            "application_status": row["application_status"],
            "file_id": row["resume_file_id"],
            "filename": row["resume_filename"],
            "text_preview": (row["latest_resume_text"] or "")[:200],
            "candidate_id": row["candidate_id"],
            "candidate_name": row["candidate_name"],
            "candidate_email": row["candidate_email"],
            "candidate_phone": row["candidate_phone"],
            "match_score": row["match_score"],
            "shortlist_status": row["shortlist_status"],
            "profile": json.loads(row["profile_json"]) if row["profile_json"] else {}
        })
    return resumes

