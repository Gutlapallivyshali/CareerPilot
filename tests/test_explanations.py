import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import requests
from fastapi import HTTPException
from google.genai import errors
from streamlit.testing.v1 import AppTest

import backend.app.services.ai_explainer as ai_explainer
from backend.app.routers.explanations import explain_job_for_profile

FRONTEND_APP_PATH = str(Path(__file__).resolve().parents[1] / "frontend" / "app.py")


def _make_profile(**overrides):
    data = {
        "id": 4,
        "name": "Test Candidate",
        "education": "B.Tech CSE",
        "skills": "Java, Python, SQL, FastAPI, Machine Learning",
        "interests": "Software Development, AI, Backend Development",
        "preferred_location": "Hyderabad, Bengaluru, Remote",
        "experience_level": "Fresher",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _make_job(**overrides):
    data = {
        "id": 1,
        "title": "Python Developer Intern",
        "company": "TechNova",
        "location": "Bengaluru",
        "job_type": "Internship",
        "required_skills": "Python, SQL, FastAPI, Git",
        "description": "Work on Python backend APIs and database integration.",
        "experience_level": "Fresher",
        "apply_url": "https://example.com/python-intern",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _make_mock_db(profile, job, all_jobs):
    db = MagicMock()

    def query_side_effect(model):
        q = MagicMock()
        if getattr(model, "__tablename__", "") == "user_profiles":
            q.filter.return_value.first.return_value = profile
        elif getattr(model, "__tablename__", "") == "jobs":
            q.filter.return_value.first.return_value = job
            q.all.return_value = all_jobs
        return q

    db.query.side_effect = query_side_effect
    return db


class RuleBasedFallbackTests(unittest.TestCase):
    def test_rule_based_identifies_matching_and_missing_skills_accurately(self):
        profile = _make_profile()
        job = _make_job()

        text = ai_explainer.generate_rule_based_explanation(
            profile,
            job,
            match_score=44.5,
        )

        self.assertIn("Rule-based explanation (Gemini temporarily unavailable)", text)
        self.assertIn("44.5%", text)
        self.assertIn("Matching Skills (from your profile):** Python, SQL, FastAPI", text)
        self.assertIn("Missing Skills (to learn/add):** Git", text)
        self.assertIn("Backend Development", text)

    def test_rule_based_does_not_confuse_java_with_javascript(self):
        profile = _make_profile(skills="Java, Python, SQL")
        frontend_job = _make_job(
            id=7,
            title="Frontend Developer Intern",
            company="PixelCraft",
            location="Chennai",
            required_skills="HTML, CSS, JavaScript, React",
            description="Build responsive user interfaces for web applications.",
        )

        text = ai_explainer.generate_rule_based_explanation(
            profile,
            frontend_job,
            match_score=5.2,
        )

        self.assertIn("Rule-based explanation (Gemini temporarily unavailable)", text)
        self.assertIn("Matching Skills (from your profile):** None matched", text)
        self.assertIn(
            "Missing Skills (to learn/add):** HTML, CSS, JavaScript, React",
            text,
        )

    def test_gemini_success_returns_primary_explanation(self):
        profile = _make_profile()
        job = _make_job()
        mock_response = MagicMock()
        mock_response.text = "- Strong match in Python, SQL, and FastAPI.\n- Learn Git."

        dummy_client = MagicMock()
        dummy_client.models.generate_content.return_value = mock_response

        with patch.object(ai_explainer, "client", dummy_client):
            result = ai_explainer.explain_job_match_with_metadata(
                profile,
                job,
                match_score=44.5,
            )

        self.assertEqual(result["source"], "gemini")
        self.assertIsNone(result["fallback_reason"])
        self.assertEqual(result["explanation"], mock_response.text)

    def test_gemini_429_503_timeout_and_generic_error_fall_back_gracefully(self):
        profile = _make_profile()
        job = _make_job()

        error_cases = [
            errors.ClientError(
                429,
                {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "Quota exceeded"}},
            ),
            errors.ServerError(
                503,
                {"error": {"code": 503, "status": "UNAVAILABLE", "message": "High demand"}},
            ),
            TimeoutError("Request timed out"),
            RuntimeError("Unexpected client error"),
        ]

        for exc in error_cases:
            with self.subTest(error=type(exc).__name__):
                dummy_client = MagicMock()
                dummy_client.models.generate_content.side_effect = exc

                with patch.object(ai_explainer, "client", dummy_client):
                    result = ai_explainer.explain_job_match_with_metadata(
                        profile,
                        job,
                        match_score=44.5,
                    )

                self.assertEqual(result["source"], "rule_based_fallback")
                self.assertIsNotNone(result["fallback_reason"])
                self.assertIn(
                    "Rule-based explanation (Gemini temporarily unavailable)",
                    result["explanation"],
                )
                self.assertIn("Git", result["explanation"])


class ExplanationRouterTests(unittest.TestCase):
    def test_router_returns_fallback_with_match_score_on_gemini_failure(self):
        profile = _make_profile()
        job = _make_job()
        mock_db = _make_mock_db(profile, job, [job])
        err_503 = errors.ServerError(
            503,
            {"error": {"code": 503, "status": "UNAVAILABLE", "message": "High demand"}},
        )
        dummy_client = MagicMock()
        dummy_client.models.generate_content.side_effect = err_503

        with patch("backend.app.routers.explanations.SessionLocal", return_value=mock_db), \
             patch.object(ai_explainer, "client", dummy_client):
            response = explain_job_for_profile(job_id=1, profile_id=4)

        self.assertEqual(response["explanation_source"], "rule_based_fallback")
        self.assertIsInstance(response["match_score"], float)
        self.assertIn(
            "Rule-based explanation (Gemini temporarily unavailable)",
            response["explanation"],
        )
        mock_db.close.assert_called_once()

    def test_router_returns_gemini_explanation_when_available(self):
        profile = _make_profile()
        job = _make_job()
        mock_db = _make_mock_db(profile, job, [job])
        mock_resp = MagicMock()
        mock_resp.text = "AI explanation: Python and FastAPI fit well."
        dummy_client = MagicMock()
        dummy_client.models.generate_content.return_value = mock_resp

        with patch("backend.app.routers.explanations.SessionLocal", return_value=mock_db), \
             patch.object(ai_explainer, "client", dummy_client):
            response = explain_job_for_profile(job_id=1, profile_id=4)

        self.assertEqual(response["explanation_source"], "gemini")
        self.assertIsNone(response["fallback_reason"])
        self.assertEqual(response["explanation"], mock_resp.text)
        mock_db.close.assert_called_once()

    def test_router_raises_404_when_profile_missing(self):
        mock_db = _make_mock_db(None, None, [])
        with patch("backend.app.routers.explanations.SessionLocal", return_value=mock_db):
            with self.assertRaises(HTTPException) as ctx:
                explain_job_for_profile(job_id=1, profile_id=999)
        self.assertEqual(ctx.exception.status_code, 404)
        mock_db.close.assert_called_once()


class StreamlitExplanationUITests(unittest.TestCase):
    def _mock_response(self, status_code, payload):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = payload
        resp.text = str(payload)
        return resp

    def test_streamlit_renders_gemini_and_fallback_explanations(self):
        rec_job = {
            "id": 1,
            "title": "Python Developer Intern",
            "company": "TechNova",
            "location": "Bengaluru",
            "required_skills": "Python, SQL, FastAPI, Git",
            "description": "Work on Python backend APIs and database integration.",
            "match_score": 44.5,
            "apply_url": "https://example.com/python-intern",
        }

        def make_handler(explain_payload):
            def handler(session_self, method, url, **kwargs):
                if url.endswith("/health"):
                    return self._mock_response(200, {"status": "healthy"})
                if "/api/jobs/recommend/profile/" in url:
                    return self._mock_response(
                        200,
                        {
                            "profile_id": 4,
                            "candidate_name": "Test Candidate",
                            "total_jobs": 1,
                            "recommendations": [rec_job],
                        },
                    )
                if "/explain/" in url:
                    return self._mock_response(200, explain_payload)
                return self._mock_response(404, {"detail": "Not found"})
            return handler

        # Case 1: Rule-based fallback
        fallback_payload = {
            "explanation_source": "rule_based_fallback",
            "explanation": "**Rule-based explanation (Gemini temporarily unavailable)**\n\nMatching Skills: Python, SQL, FastAPI\nMissing Skills: Git",
        }
        with patch.object(requests.Session, "request", make_handler(fallback_payload)):
            at = AppTest.from_file(FRONTEND_APP_PATH, default_timeout=20)
            at.run()
            at.session_state["profile_id"] = 4
            [b for b in at.button if "Find My Matching Jobs" in b.label][0].click().run()
            [b for b in at.button if "Explain Match" in b.label][0].click().run()

            self.assertFalse(at.exception)
            self.assertFalse(any("Explanation failed" in e.value for e in at.error))
            self.assertFalse(any("Could not connect to the backend" in e.value for e in at.error))
            self.assertTrue(
                any("Rule-based explanation (Gemini temporarily unavailable)" in m.value for m in at.markdown)
            )

        # Case 2: Gemini primary success
        gemini_payload = {
            "explanation_source": "gemini",
            "explanation": "Gemini says you match Python and FastAPI well.",
        }
        with patch.object(requests.Session, "request", make_handler(gemini_payload)):
            at = AppTest.from_file(FRONTEND_APP_PATH, default_timeout=20)
            at.run()
            at.session_state["profile_id"] = 4
            [b for b in at.button if "Find My Matching Jobs" in b.label][0].click().run()
            [b for b in at.button if "Explain Match" in b.label][0].click().run()

            self.assertFalse(at.exception)
            self.assertTrue(
                any("Gemini's Job Match Explanation" in m.value for m in at.markdown)
            )
            self.assertTrue(
                any("Gemini says you match Python and FastAPI well." in m.value for m in at.markdown)
            )


if __name__ == "__main__":
    unittest.main()
