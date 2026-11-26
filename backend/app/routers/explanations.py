
from fastapi import APIRouter, HTTPException

from backend.app.database import SessionLocal
from backend.app.models import Job, UserProfile
from backend.app.services.ai_explainer import explain_job_match_with_metadata
from backend.app.services.job_matcher import rank_jobs

router = APIRouter()


@router.get("/api/jobs/{job_id}/explain/profile/{profile_id}")
def explain_job_for_profile(job_id: int, profile_id: int):

    db = SessionLocal()

    try:
        # Find the candidate profile
        profile = db.query(UserProfile).filter(
            UserProfile.id == profile_id
        ).first()

        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Profile not found"
            )

        # Find the selected job
        job = db.query(Job).filter(
            Job.id == job_id
        ).first()

        if not job:
            raise HTTPException(
                status_code=404,
                detail="Job not found"
            )

        # Compute existing TF-IDF match score for this job and profile
        all_jobs = db.query(Job).all()
        query = f"""
        Skills: {profile.skills or ""}
        Interests: {profile.interests or ""}
        Education: {profile.education or ""}
        Preferred Location: {profile.preferred_location or ""}
        Experience Level: {profile.experience_level or ""}
        """
        ranked_jobs = rank_jobs(query, all_jobs)
        match_score = next(
            (item["match_score"] for item in ranked_jobs if item["id"] == job.id),
            None,
        )

        # Ask Gemini to explain the match, with rule-based fallback if unavailable
        result = explain_job_match_with_metadata(
            profile,
            job,
            match_score=match_score,
        )

        return {
            "profile_id": profile.id,
            "candidate_name": profile.name,
            "job_id": job.id,
            "job_title": job.title,
            "company": job.company,
            "match_score": match_score,
            "explanation_source": result["source"],
            "fallback_reason": result["fallback_reason"],
            "explanation": result["explanation"],
        }

    finally:
        db.close()
