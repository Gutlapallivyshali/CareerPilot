
from backend.app.database import SessionLocal
from backend.app.models import Job


sample_jobs = [
    {
        "title": "Python Developer Intern",
        "company": "TechNova",
        "location": "Bengaluru",
        "job_type": "Internship",
        "required_skills": "Python, SQL, FastAPI, Git",
        "description": "Work on Python backend APIs and database integration.",
        "experience_level": "Fresher",
        "apply_url": "https://example.com/python-intern"
    },
    {
        "title": "Java Developer Intern",
        "company": "CodeSphere",
        "location": "Hyderabad",
        "job_type": "Internship",
        "required_skills": "Java, OOP, SQL, Spring Boot",
        "description": "Develop backend applications using Java and Spring Boot.",
        "experience_level": "Fresher",
        "apply_url": "https://example.com/java-intern"
    },
    {
        "title": "Machine Learning Intern",
        "company": "DataMind",
        "location": "Remote",
        "job_type": "Internship",
        "required_skills": "Python, Machine Learning, Pandas, Scikit-learn",
        "description": "Build and evaluate machine learning models.",
        "experience_level": "Fresher",
        "apply_url": "https://example.com/ml-intern"
    },
    {
        "title": "AI Engineering Intern",
        "company": "FutureAI",
        "location": "Bengaluru",
        "job_type": "Internship",
        "required_skills": "Python, LLM, Prompt Engineering, APIs",
        "description": "Experiment with LLM applications and AI-powered features.",
        "experience_level": "Fresher",
        "apply_url": "https://example.com/ai-intern"
    },
    {
        "title": "Data Analyst Intern",
        "company": "InsightWorks",
        "location": "Hyderabad",
        "job_type": "Internship",
        "required_skills": "Python, SQL, Excel, Pandas",
        "description": "Analyze datasets and prepare reports.",
        "experience_level": "Fresher",
        "apply_url": "https://example.com/data-intern"
    },
    {
        "title": "Backend Developer Intern",
        "company": "CloudBridge",
        "location": "Remote",
        "job_type": "Internship",
        "required_skills": "Python, FastAPI, REST APIs, SQL, Git",
        "description": "Build and test REST APIs for backend services.",
        "experience_level": "Fresher",
        "apply_url": "https://example.com/backend-intern"
    },
    {
        "title": "Frontend Developer Intern",
        "company": "PixelCraft",
        "location": "Chennai",
        "job_type": "Internship",
        "required_skills": "HTML, CSS, JavaScript, React",
        "description": "Build responsive user interfaces for web applications.",
        "experience_level": "Fresher",
        "apply_url": "https://example.com/frontend-intern"
    },
    {
        "title": "Software Development Intern",
        "company": "DevWorks",
        "location": "Remote",
        "job_type": "Internship",
        "required_skills": "Java, Python, DSA, SQL, Git",
        "description": "Contribute to software development and problem solving.",
        "experience_level": "Fresher",
        "apply_url": "https://example.com/sde-intern"
    }
]


def seed_jobs():
    db = SessionLocal()

    try:
        existing_count = db.query(Job).count()

        if existing_count > 0:
            print(f"Database already contains {existing_count} jobs.")
            return

        jobs = [Job(**job) for job in sample_jobs]

        db.add_all(jobs)
        db.commit()

        print(f"Successfully added {len(jobs)} sample jobs!")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_jobs()
