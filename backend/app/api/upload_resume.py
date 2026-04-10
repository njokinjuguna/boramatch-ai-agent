from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

import os
import pickle

from app.utils.drive_utils import upload_to_drive
from app.utils.resume_parser import parse_resume, build_candidate_profile
from app.data.resume_db import (
    upsert_candidate,
    application_exists,
    create_application,
    get_candidate_by_email,
)

load_dotenv()
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

router = APIRouter()
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def encode_text(text: str):
    return model.encode(text)


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...), job_id: str = Form(...)):
    if not file.filename.endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF or DOCX files are allowed.")

    try:
        # Step 1: parse resume
        file.file.seek(0)
        parsed = parse_resume(file)

        resume_text = parsed.get("cleaned_text", "")
        raw_preview = parsed.get("text_preview", "")

        if not resume_text:
            raise HTTPException(status_code=500, detail="Failed to extract text from resume.")

        candidate_name = parsed.get("name", "Not found")
        candidate_email = parsed.get("email", "Not found")
        candidate_phone = parsed.get("phone", "Not found")

        # ATS uniqueness depends on email
        if not candidate_email or candidate_email == "Not found":
            raise HTTPException(
                status_code=400,
                detail="Could not detect a valid email address from the resume. Please include an email address in your CV."
            )

        # Step 2: duplicate application check BEFORE Drive upload
        existing_candidate = get_candidate_by_email(candidate_email)
        if existing_candidate:
            existing_candidate_id = existing_candidate["candidate_id"]
            if application_exists(existing_candidate_id, job_id):
                return {
                    "status": "duplicate",
                    "job_id": job_id,
                    "candidate_id": existing_candidate_id,
                    "candidate_email": candidate_email,
                    "message": "You have already applied for this role using this email address."
                }

        # Step 3: build candidate profile
        profile = build_candidate_profile(raw_preview if raw_preview else resume_text)

        # Step 4: compute embedding
        embedding = encode_text(resume_text)
        embedding_blob = pickle.dumps(embedding)

        # Step 5: upload to Drive only after duplicate check passes
        file.file.seek(0)
        file_id = upload_to_drive(file, FOLDER_ID)

        # Step 6: upsert candidate globally by email
        candidate_id, candidate_action = upsert_candidate(
            name=candidate_name,
            email=candidate_email,
            phone=candidate_phone,
            latest_resume_file_id=file_id,
            latest_resume_filename=file.filename,
            latest_resume_text=resume_text,
            latest_embedding=embedding_blob,
            profile=profile,
        )

        # Step 7: create application for this specific job
        application_id = create_application(
            candidate_id=candidate_id,
            job_id=job_id,
            resume_file_id=file_id,
            resume_filename=file.filename,
            application_status="applied",
        )

        return {
            "status": "success",
            "application_id": application_id,
            "candidate_id": candidate_id,
            "candidate_action": candidate_action,
            "file_id": file_id,
            "job_id": job_id,
            "message": f"{file.filename} uploaded successfully.",
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "candidate_phone": candidate_phone,
            "profile": profile,
            "preview": raw_preview[:300] if raw_preview else resume_text[:300]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/extract")
async def extract_text_from_resume(file: UploadFile = File(...)):
    if not file.filename.endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF or DOCX files are allowed.")

    try:
        file.file.seek(0)
        parsed = parse_resume(file)

        return {
            "status": "success",
            "preview": parsed.get("text_preview", "")[:500],
            "candidate_name": parsed.get("name", "Not found"),
            "candidate_email": parsed.get("email", "Not found"),
            "candidate_phone": parsed.get("phone", "Not found"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {str(e)}")


__all__ = ["router"]