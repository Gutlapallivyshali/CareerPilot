
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.app.database import SessionLocal
from backend.app.models import UserProfile

router = APIRouter()


class ProfileRequest(BaseModel):
    name: str
    education: str = ""
    skills: str = ""
    interests: str = ""
    preferred_location: str = ""
    experience_level: str = "Fresher"


@router.post("/api/profile")
def create_profile(profile: ProfileRequest):

    db = SessionLocal()

    try:
        new_profile = UserProfile(
            name=profile.name,
            education=profile.education,
            skills=profile.skills,
            interests=profile.interests,
            preferred_location=profile.preferred_location,
            experience_level=profile.experience_level
        )

        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)

        return {
            "message": "Profile created successfully!",
            "profile_id": new_profile.id
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@router.get("/api/profile/{profile_id}")
def get_profile(profile_id: int):

    db = SessionLocal()

    try:
        profile = db.query(UserProfile).filter(
            UserProfile.id == profile_id
        ).first()

        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Profile not found"
            )

        return {
            "id": profile.id,
            "name": profile.name,
            "education": profile.education,
            "skills": profile.skills,
            "interests": profile.interests,
            "preferred_location": profile.preferred_location,
            "experience_level": profile.experience_level
        }

    finally:
        db.close()
