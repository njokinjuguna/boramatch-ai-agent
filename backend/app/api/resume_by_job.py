from fastapi import APIRouter, HTTPException, Query
from app.data.resume_db import get_resumes_by_job_id

router = APIRouter()

@router.get("/resume/by-job")
async def resumes_for_job(job_id: str = Query(...)):
    try:
        resumes = get_resumes_by_job_id(job_id)
        return {"status": "success", "resumes": resumes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching resumes: {str(e)}")
