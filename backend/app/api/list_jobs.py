from fastapi import APIRouter, HTTPException
from app.data.job_post_db import get_all_jobs

router = APIRouter()

@router.get("/job/list")
async def list_jobs():
    try:
        jobs = get_all_jobs()
        return {"status": "success", "jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching job list: {str(e)}")
