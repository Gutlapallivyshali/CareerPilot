
from fastapi import APIRouter, HTTPException
from sqlalchemy import or_
from backend.app.services.job_matcher import rank_jobs
from backend.app.database import SessionLocal
from backend.app.models import Job, UserProfile

router = APIRouter()


# Get all jobs
@router.get("/api/jobs")
def get_all_jobs():
    db = SessionLocal()

    try:
        jobs = db.query(Job).all()

        return [
            {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "job_type": job.job_type,
                "required_skills": job.required_skills,
                "description": job.description,
                "experience_level": job.experience_level,
                "apply_url": job.apply_url
            }
            for job in jobs
        ]

    finally:
        db.close()


# Search jobs using keyword and location
@router.get("/api/jobs/search")
def search_jobs(keyword: str = "", location: str = ""):
    db = SessionLocal()

    try:
        query = db.query(Job)

        if keyword:
            search_term = f"%{keyword}%"

            query = query.filter(
                or_(
                    Job.title.ilike(search_term),
                    Job.company.ilike(search_term),
                    Job.required_skills.ilike(search_term),
                    Job.description.ilike(search_term)
                )
            )

        if location:
            query = query.filter(
                Job.location.ilike(f"%{location}%")
            )

        jobs = query.all()

        return [
            {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "required_skills": job.required_skills,
                "description": job.description,
                "apply_url": job.apply_url
            }
            for job in jobs
        ]

    finally:
        db.close()

# Get ranked job recommendations
@router.get("/api/jobs/recommend")
def recommend_jobs(query: str):

    db = SessionLocal()

    try:
        jobs = db.query(Job).all()

        ranked_jobs = rank_jobs(query, jobs)

        return {
            "search_query": query,
            "total_jobs": len(ranked_jobs),
            "recommendations": ranked_jobs
        }

    finally:
        db.close()


@router.get("/api/jobs/recommend/profile/{profile_id}")
def recommend_jobs_for_profile(profile_id: int):

    db = SessionLocal()

    try:
        # Step 1: Retrieve the candidate profile
        profile = db.query(UserProfile).filter(
            UserProfile.id == profile_id
        ).first()

        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Profile not found"
            )

        # Step 2: Retrieve all available demo jobs
        jobs = db.query(Job).all()

        # Step 3: Build a personalized search query
        query = f"""
        Skills: {profile.skills or ""}
        Interests: {profile.interests or ""}
        Education: {profile.education or ""}
        Preferred Location: {profile.preferred_location or ""}
        Experience Level: {profile.experience_level or ""}
        """

        # Step 4: Rank jobs using our existing TF-IDF matcher
        ranked_jobs = rank_jobs(query, jobs)

        return {
            "profile_id": profile.id,
            "candidate_name": profile.name,
            "personalized_query": query.strip(),
            "total_jobs": len(ranked_jobs),
            "recommendations": ranked_jobs
        }

    finally:
        db.close()
