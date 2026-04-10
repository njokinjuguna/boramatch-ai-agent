from fastapi import FastAPI
from app.api.upload_resume import router as upload_router
from app.api.view_resumes import router as view_router
from app.api.match_resumes import router as match_router
from app.data.resume_db import init_resume_db
from app.data.job_post_db import init_job_db
from app.api.list_jobs import router as list_jobs_router
from app.api.resume_by_job import router as resume_router
from app.api.job_postings import router as job_posting_router


app= FastAPI()
@app.on_event("startup")
async def startup_event():
    init_resume_db()
    init_job_db()
app.include_router(upload_router)
app.include_router(view_router)
app.include_router(match_router)
app.include_router(job_posting_router)
app.include_router(resume_router)
app.include_router(list_jobs_router)