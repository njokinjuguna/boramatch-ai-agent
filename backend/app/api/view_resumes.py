from fastapi import APIRouter
from app.data.store import resume_store
router=APIRouter()
@router.get("/resumes")
def get_all_resumes():
    return resume_store