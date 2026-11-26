
from fastapi import FastAPI
from backend.app.routers.profile import router as profile_router
from backend.app.database import Base, engine
from backend.app import models
from backend.app.routers.jobs import router as jobs_router
from backend.app.routers.explanations import router as explanations_router
from backend.app.seed import seed_jobs

app = FastAPI(
    title="CareerPilot API",
    description="AI-powered Job Search Assistant",
    version="1.0.0"
)
app.include_router(jobs_router)
app.include_router(profile_router)
app.include_router(explanations_router)
# Create database tables
Base.metadata.create_all(bind=engine)
seed_jobs()


@app.get("/")
def home():
    return {
        "message": "Welcome to CareerPilot!",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }
