
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite database file will be created in the CareerPilot folder
DATABASE_URL = "sqlite:///./careerpilot.db"

# Connect Python to SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Create database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for our database models
Base = declarative_base()
