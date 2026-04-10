import sqlite3
import json

JOB_DB_PATH = "job_post.db"


def get_job_db_connection():
    conn = sqlite3.connect(JOB_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_job_db():
    with get_job_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_postings (
                job_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                requirements_json TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def insert_job(job_id: str, title: str, description: str, requirements: dict | None = None):
    conn = get_job_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO job_postings (job_id, title, description, requirements_json)
        VALUES (?, ?, ?, ?)
    """, (
        job_id,
        title,
        description,
        json.dumps(requirements or {})
    ))
    conn.commit()
    conn.close()


def update_job_requirements(job_id: str, requirements: dict):
    conn = get_job_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE job_postings
        SET requirements_json = ?
        WHERE job_id = ?
    """, (json.dumps(requirements or {}), job_id))
    conn.commit()
    conn.close()


def get_latest_job():
    conn = get_job_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT job_id, title, description, requirements_json
        FROM job_postings
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "job_id": row["job_id"],
        "title": row["title"],
        "description": row["description"],
        "requirements": json.loads(row["requirements_json"]) if row["requirements_json"] else {}
    }


def get_all_jobs():
    conn = get_job_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT job_id, title, description, requirements_json, timestamp
        FROM job_postings
        ORDER BY timestamp DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    jobs = []
    for row in rows:
        jobs.append({
            "job_id": row["job_id"],
            "title": row["title"],
            "description": row["description"],
            "requirements": json.loads(row["requirements_json"]) if row["requirements_json"] else {},
            "created_at": row["timestamp"]
        })
    return jobs


def get_job_by_id(job_id: str):
    conn = get_job_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT job_id, title, description, requirements_json
        FROM job_postings
        WHERE job_id = ?
    """, (job_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "job_id": row["job_id"],
        "title": row["title"],
        "description": row["description"],
        "requirements": json.loads(row["requirements_json"]) if row["requirements_json"] else {}
    }