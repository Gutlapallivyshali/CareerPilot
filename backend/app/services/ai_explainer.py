
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

# Load environment variables from the CareerPilot project root
ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# Read the API key securely from .env
api_key = os.getenv("GEMINI_API_KEY")

# Create the Gemini client only when a key is available (with bounded HTTP timeout)
GEMINI_TIMEOUT_MS = 25000
client = (
    genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
    )
    if api_key
    else None
)

FALLBACK_LABEL = "Rule-based explanation (Gemini temporarily unavailable)"

_INTEREST_STOPWORDS = {
    "and", "or", "the", "a", "an", "in", "of", "for", "to", "with",
    "development", "engineering", "engineer", "developer", "intern",
    "internship", "role", "roles", "career", "field", "work", "jobs",
}


class AIServiceError(Exception):
    """Error raised when the Gemini explanation service cannot fulfill a request."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def _parse_csv_items(raw_text):
    """Parse comma/semicolon/newline-separated items while preserving order and original case."""
    if not raw_text:
        return []
    seen = set()
    items = []
    for part in re.split(r"[,;\n|]+", str(raw_text)):
        cleaned = re.sub(r"\s+", " ", part).strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key not in seen:
            seen.add(key)
            items.append(cleaned)
    return items


def _normalize_skill(skill):
    """Normalize a skill string for accurate comparison without false substring matches."""
    norm = re.sub(r"\s+", " ", skill.strip().lower())
    # Allow safe singular/plural normalization for multi-character non-double-s terms (e.g. REST API / REST APIs)
    if len(norm) > 3 and norm.endswith("s") and not norm.endswith("ss"):
        return norm[:-1]
    return norm


def _contains_whole_term(text, term):
    """Return True if term appears in text as a whole word/phrase."""
    if not text or not term:
        return False
    pattern = rf"(?<!\w){re.escape(term.lower())}(?!\w)"
    return re.search(pattern, text.lower()) is not None


def _find_interest_matches(interests, job_text):
    """Find candidate interests that genuinely align with the job title, description, or skills."""
    matched = []
    for interest in interests:
        if _contains_whole_term(job_text, interest):
            matched.append(interest)
            continue
        keywords = [
            word for word in re.findall(r"[a-zA-Z0-9+#.-]+", interest.lower())
            if len(word) >= 2 and word not in _INTEREST_STOPWORDS
        ]
        if any(_contains_whole_term(job_text, kw) for kw in keywords):
            matched.append(interest)
    return matched


def generate_rule_based_explanation(profile, job, match_score=None):
    """
    Generate an accurate rule-based explanation using candidate profile and job data
    when Gemini AI is unavailable.
    """
    candidate_skills = _parse_csv_items(getattr(profile, "skills", ""))
    required_skills = _parse_csv_items(getattr(job, "required_skills", ""))
    candidate_interests = _parse_csv_items(getattr(profile, "interests", ""))
    preferred_locations = _parse_csv_items(getattr(profile, "preferred_location", ""))

    candidate_skill_keys = {_normalize_skill(skill) for skill in candidate_skills}

    matching_skills = []
    missing_skills = []
    for req in required_skills:
        if _normalize_skill(req) in candidate_skill_keys:
            matching_skills.append(req)
        else:
            missing_skills.append(req)

    job_title = getattr(job, "title", "") or "this role"
    job_company = getattr(job, "company", "") or "the company"
    job_description = (getattr(job, "description", "") or "").strip()
    job_location = (getattr(job, "location", "") or "").strip()
    job_exp = (getattr(job, "experience_level", "") or "").strip()
    profile_exp = (getattr(profile, "experience_level", "") or "").strip()

    job_text = " ".join([
        job_title,
        job_description,
        getattr(job, "required_skills", "") or "",
    ])
    matched_interests = _find_interest_matches(candidate_interests, job_text)

    # 1. Why this job is relevant
    relevance_bullets = []
    if match_score is not None:
        if match_score >= 50:
            score_note = "strong TF-IDF profile-to-job match"
        elif match_score >= 20:
            score_note = "moderate TF-IDF profile-to-job match"
        else:
            score_note = "low TF-IDF text overlap with your current profile"
        relevance_bullets.append(
            f"- **Match Score:** {match_score}% ({score_note})."
        )

    if required_skills:
        if matching_skills:
            relevance_bullets.append(
                f"- **Skill Relevance:** Your profile matches {len(matching_skills)} of {len(required_skills)} "
                f"required skills (**{', '.join(matching_skills)}**) for **{job_title}** at **{job_company}**."
            )
        else:
            relevance_bullets.append(
                f"- **Skill Relevance:** None of the listed required skills (**{', '.join(required_skills)}**) "
                f"were found in your current profile skills for **{job_title}** at **{job_company}**."
            )
    else:
        relevance_bullets.append(
            f"- **Role Focus:** **{job_title}** at **{job_company}** did not list specific required skills."
        )

    if matched_interests:
        relevance_bullets.append(
            f"- **Interest Alignment:** Your stated interests (**{', '.join(matched_interests)}**) align with this role's title and description."
        )
    elif job_description:
        relevance_bullets.append(
            f"- **Role Description:** {job_description}"
        )

    location_matched = (
        job_location
        and preferred_locations
        and any(loc.lower() == job_location.lower() for loc in preferred_locations)
    )
    if location_matched:
        relevance_bullets.append(
            f"- **Location Match:** **{job_location}** is in your preferred locations."
        )
    if profile_exp and job_exp and profile_exp.lower() == job_exp.lower():
        relevance_bullets.append(
            f"- **Experience Level:** Matches your **{profile_exp}** experience level."
        )

    # 2. Skill breakdown
    matching_text = (
        ", ".join(matching_skills)
        if matching_skills
        else ("None listed in your profile" if not candidate_skills else "None matched")
    )
    missing_text = (
        ", ".join(missing_skills)
        if missing_skills
        else ("None (all listed required skills are in your profile)" if required_skills else "None listed by job")
    )

    # 3. Suggested skills to improve
    if missing_skills:
        improvement_bullets = [
            f"- Prioritize learning or practicing **{', '.join(missing_skills)}**, which are required for **{job_title}** but not currently listed in your profile."
        ]
        if job_description:
            improvement_bullets.append(
                f"- Review how these skills apply to the role's responsibilities: \"{job_description}\""
            )
    elif required_skills:
        improvement_bullets = [
            f"- You already list all required skills (**{', '.join(required_skills)}**) in your profile.",
            f"- Strengthen hands-on projects related to **{job_title}**"
            + (f" ({job_description})" if job_description else ".")
        ]
    else:
        improvement_bullets = [
            f"- Review the job description for **{job_title}** and highlight relevant projects in your profile."
        ]

    sections = [
        f"**{FALLBACK_LABEL}**",
        "**1. Why This Job May Match Your Profile**",
        "\n".join(relevance_bullets),
        "**2. Matching & Missing Skills**",
        f"- **Matching Skills (from your profile):** {matching_text}\n- **Missing Skills (to learn/add):** {missing_text}",
        "**3. Suggested Skills to Improve**",
        "\n".join(improvement_bullets),
    ]
    return "\n\n".join(sections)


def _call_gemini_explanation(profile, job):
    """Request an explanation from Gemini and raise AIServiceError on failure."""
    prompt = f"""
    You are a helpful career guidance assistant.

    Candidate profile:
    Skills: {profile.skills or ""}
    Interests: {profile.interests or ""}
    Education: {profile.education or ""}
    Experience level: {profile.experience_level or ""}

    Job details:
    Title: {job.title}
    Company: {job.company}
    Required skills: {job.required_skills or ""}
    Description: {job.description or ""}
    Experience level: {job.experience_level or ""}

    Explain:
    1. Why this job may match the candidate.
    2. Which candidate skills are relevant.
    3. What skills the candidate may need to learn.

    Use simple English and concise bullet points.
    Do not guarantee that the candidate will be hired.
    """

    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

        if not response.text:
            raise AIServiceError(
                502,
                "Gemini AI returned an empty explanation."
            )

        return response.text

    except AIServiceError:
        raise

    except errors.APIError as error:
        code = getattr(error, "code", None)
        status = getattr(error, "status", None)
        print("Gemini API Error:", type(error).__name__, code, status)

        if code == 429 or status == "RESOURCE_EXHAUSTED":
            raise AIServiceError(
                429,
                "Gemini AI rate limit or quota reached (429)."
            ) from error

        if code == 503 or status == "UNAVAILABLE":
            raise AIServiceError(
                503,
                "Gemini AI is temporarily experiencing high demand (503)."
            ) from error

        raise AIServiceError(
            502,
            "Gemini AI could not generate an explanation right now."
        ) from error

    except TimeoutError as error:
        print("Gemini API Timeout:", type(error).__name__)
        raise AIServiceError(
            504,
            "Gemini AI took too long to respond."
        ) from error

    except Exception as error:
        print("Gemini API Error:", type(error).__name__)
        if "timeout" in type(error).__name__.lower() or "timed out" in str(error).lower():
            raise AIServiceError(
                504,
                "Gemini AI took too long to respond."
            ) from error
        raise AIServiceError(
            502,
            "Gemini AI could not generate an explanation right now."
        ) from error


def explain_job_match_with_metadata(profile, job, match_score=None):
    """
    Generate a job match explanation using Gemini as primary and a rule-based
    fallback when Gemini is unavailable or fails.
    """
    if client is None:
        return {
            "explanation": generate_rule_based_explanation(
                profile,
                job,
                match_score=match_score,
            ),
            "source": "rule_based_fallback",
            "fallback_reason": "Gemini API key is not configured.",
        }

    try:
        explanation = _call_gemini_explanation(profile, job)
        return {
            "explanation": explanation,
            "source": "gemini",
            "fallback_reason": None,
        }
    except AIServiceError as error:
        return {
            "explanation": generate_rule_based_explanation(
                profile,
                job,
                match_score=match_score,
            ),
            "source": "rule_based_fallback",
            "fallback_reason": error.message,
        }


def explain_job_match(profile, job, match_score=None):
    """
    Ask Gemini to explain how a candidate matches a job, falling back to a
    rule-based explanation if Gemini is unavailable.
    """
    return explain_job_match_with_metadata(
        profile,
        job,
        match_score=match_score,
    )["explanation"]