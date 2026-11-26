# CareerPilot – AI Job Search Assistant

CareerPilot is an AI-powered job search assistant that helps candidates discover relevant internship opportunities and understand how well their profiles match job requirements.

## Features

- Candidate profile creation and management
- Job search by keyword and location
- Personalized job recommendations
- Job matching using TF-IDF and cosine similarity
- Match explanations using Google Gemini AI
- Rule-based fallback explanations when Gemini is unavailable
- FastAPI backend and Streamlit frontend
- SQLite database integration

## Tech Stack

- Python
- FastAPI
- Streamlit
- SQLAlchemy
- SQLite
- Scikit-learn
- Google Gemini API

## Project Structure

- backend/ – API, database, models, and services
- frontend/ – Streamlit user interface
- tests/ – Automated tests
- data/ – Project data
- requirements.txt – Python dependencies

## Setup and Installation

1. Clone the repository:

   git clone YOUR_GITHUB_REPOSITORY_URL

2. Navigate into the project:

   cd CareerPilot

3. Create and activate a virtual environment:

   python -m venv venv

   Windows PowerShell:
   .\venv\Scripts\Activate.ps1

4. Install dependencies:

   pip install -r requirements.txt

5. Create a .env file in the project root and add your Gemini API key:

   GEMINI_API_KEY=your_api_key_here

## Running the Application

Start the backend:

   python -m uvicorn backend.app.main:app --reload

Start the frontend in another terminal:

   python -m streamlit run frontend/app.py

Open the application at:

   http://localhost:8501

API documentation:

   http://127.0.0.1:8000/docs

## Job Matching

CareerPilot uses TF-IDF and cosine similarity to calculate profile-to-job text similarity. Match scores indicate textual relevance and are not probabilities of getting hired.

## AI Explanation

Google Gemini generates explanations for job matches. If the AI service is unavailable or its quota is exhausted, CareerPilot provides a rule-based explanation.

## Note

The current project includes sample job data for demonstration. Sample listings and application links should not be treated as verified live vacancies.

## Future Improvements

- Integration with verified live job sources
- Resume upload and skill extraction
- User authentication
- Cloud database and deployment
- Advanced recommendation improvements
