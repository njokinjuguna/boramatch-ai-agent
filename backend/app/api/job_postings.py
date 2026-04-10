from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid

from app.data.job_post_db import insert_job, get_latest_job

router = APIRouter()


class JobInput(BaseModel):
    title: str
    description: str


@router.post("/job/create")
def create_job(job: JobInput):
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    try:
        insert_job(
            job_id=job_id,
            title=job.title,
            description=job.description,
            requirements={}
        )
        return {"job_id": job_id, "message": "Job posted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/latest")
def fetch_latest_job():
    job = get_latest_job()
    if job:
        return job
    raise HTTPException(status_code=404, detail="No job posted yet.")