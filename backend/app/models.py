
from sqlalchemy import Column, Integer, String, Text
from backend.app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    company = Column(String(200), nullable=False)
    location = Column(String(150))
    job_type = Column(String(100))
    required_skills = Column(Text)
    description = Column(Text)
    experience_level = Column(String(100))
    apply_url = Column(String(500))


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    education = Column(String(200))
    skills = Column(Text)
    interests = Column(Text)
    preferred_location = Column(String(150))
    experience_level = Column(String(100))

