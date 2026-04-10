from fastapi import HTTPException

from app.utils.matching import match_resumes
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel
from app.data.job_post_db import get_job_by_id

router=APIRouter()

class JobIdRequest(BaseModel):
        job_id: str
        top_k: int = 5#optional ,default to 5

@router.post("/match")
def match_resumes_endpoint(payload: JobIdRequest):
    job = get_job_by_id(payload.job_id)
    if not job:
        raise HTTPException(status_code=400, detail="Job not found.")

    job_description = job["description"]
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is empty.")

    response = match_resumes(job_description, payload.job_id, payload.top_k)

    if not response["results"]:
        response["message"] = "No suitable matches found for the given job description."

    return response




