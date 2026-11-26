
import streamlit as st
import requests

# CareerPilot backend address
API_URL = "http://127.0.0.1:8000"


def api_request(method, path, timeout=15, **kwargs):
    """Send an HTTP request to the local FastAPI backend without proxy interference."""
    with requests.Session() as session:
        session.trust_env = False
        return session.request(
            method=method,
            url=f"{API_URL}{path}",
            timeout=timeout,
            **kwargs
        )


def extract_error_detail(response):
    """Extract a readable error message from a FastAPI error response."""
    try:
        data = response.json()
        if isinstance(data, dict) and data.get("detail"):
            return str(data["detail"])
    except ValueError:
        pass
    return response.text or f"HTTP {response.status_code}"


# Configure the Streamlit page
st.set_page_config(
    page_title="CareerPilot",
    page_icon="🎯",
    layout="wide"
)

# Application heading
st.title("🎯 CareerPilot")
st.subheader("Your AI-powered Job Search Assistant")

st.write(
    "Find internships and jobs that match your skills, "
    "interests, and career goals."
)

# Check whether the backend is running
try:
    response = api_request("GET", "/health", timeout=5)

    if response.status_code == 200:
        st.success("Backend connected successfully!")
    else:
        st.warning("Backend is responding, but health check failed.")

except requests.exceptions.Timeout:
    st.warning("Backend health check timed out. The server may be busy.")

except requests.exceptions.ConnectionError:
    st.error("Backend is not connected. Please start FastAPI.")

except requests.RequestException:
    st.warning("Could not verify backend health right now.")


# ==================================================
# CANDIDATE PROFILE
# ==================================================

st.divider()
st.header("👤 Candidate Profile")

with st.form("profile_form"):

    name = st.text_input("Full Name")

    education = st.text_input(
        "Education",
        "B.Tech CSE"
    )

    skills = st.text_area(
        "Skills",
        "Java, Python, SQL, FastAPI, Machine Learning"
    )

    interests = st.text_area(
        "Career Interests",
        "Software Development, AI, Backend Development"
    )

    preferred_location = st.text_input(
        "Preferred Locations",
        "Hyderabad, Bengaluru, Remote"
    )

    experience_level = st.selectbox(
        "Experience Level",
        ["Fresher", "Intern", "Experienced"]
    )

    submitted = st.form_submit_button("Save Profile")

    if submitted:

        if not name.strip():
            st.warning("Please enter your name.")

        else:
            profile_data = {
                "name": name,
                "education": education,
                "skills": skills,
                "interests": interests,
                "preferred_location": preferred_location,
                "experience_level": experience_level
            }

            try:
                response = api_request(
                    "POST",
                    "/api/profile",
                    json=profile_data,
                    timeout=10
                )

                if response.status_code == 200:

                    result = response.json()

                    # Store profile ID for later API calls
                    st.session_state["profile_id"] = (
                        result["profile_id"]
                    )

                    # Clear old recommendations and explanations when profile changes
                    st.session_state["recommendations"] = []
                    for key in list(st.session_state.keys()):
                        if key.startswith("explanation_"):
                            del st.session_state[key]

                    st.success("Profile saved successfully!")

                    st.write(
                        "Your Profile ID:",
                        result["profile_id"]
                    )

                else:
                    st.error(
                        f"Failed to save profile: {extract_error_detail(response)}"
                    )

            except requests.exceptions.Timeout:
                st.warning("Saving profile timed out. Please try again.")

            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the backend.")

            except (requests.RequestException, ValueError):
                st.error("Failed to save profile due to an unexpected backend response.")


# ==================================================
# PERSONALIZED JOB RECOMMENDATIONS
# ==================================================

st.divider()

st.header("💼 Personalized Job Recommendations")

st.write(
    "Find jobs that match your saved profile."
)

if st.button("Find My Matching Jobs"):

    profile_id = st.session_state.get("profile_id")

    if not profile_id:

        st.warning("Please save your profile first.")

    else:

        try:
            response = api_request(
                "GET",
                f"/api/jobs/recommend/profile/{profile_id}",
                timeout=15
            )

            if response.status_code == 200:

                result = response.json()

                # Store recommendations so they survive reruns
                st.session_state["recommendations"] = (
                    result["recommendations"]
                )

                st.success(
                    f"Found {result['total_jobs']} "
                    "job recommendations!"
                )

            elif response.status_code == 404:

                st.error(
                    "Profile not found. Please save your profile again."
                )

            else:

                st.error(f"API error: {extract_error_detail(response)}")

        except requests.exceptions.Timeout:
            st.warning("Loading job recommendations timed out. Please try again.")

        except requests.exceptions.ConnectionError:
            st.error("Could not connect to the backend.")

        except (requests.RequestException, ValueError):
            st.error("Failed to load recommendations due to an unexpected backend response.")


# Display saved recommendations
recommendations = st.session_state.get(
    "recommendations",
    []
)
current_profile_id = st.session_state.get("profile_id")

for job in recommendations:

    with st.container(border=True):

        st.subheader(job["title"])

        st.write(f"**Company:** {job['company']}")

        st.write(f"**Location:** {job['location']}")

        st.write(
            f"**Match Score:** {job['match_score']}%"
        )

        st.write(
            f"**Required Skills:** "
            f"{job['required_skills']}"
        )

        st.write(job["description"])

        explanation_key = f"explanation_{current_profile_id}_{job['id']}"

        # Request Gemini explanation
        if st.button(
            "✨ Explain Match",
            key=f"explain_{job['id']}"
        ):

            if not current_profile_id:

                st.warning("Please save your profile first.")

            else:

                try:
                    response = api_request(
                        "GET",
                        f"/api/jobs/{job['id']}/explain/profile/{current_profile_id}",
                        timeout=40
                    )

                    if response.status_code == 200:

                        result = response.json()
                        explanation = result["explanation"]
                        explanation_source = result.get(
                            "explanation_source",
                            "gemini"
                        )

                        # Save explanation and source for this profile and job
                        st.session_state[explanation_key] = explanation
                        st.session_state[
                            f"{explanation_key}_source"
                        ] = explanation_source

                    elif response.status_code in (429, 503, 504):

                        st.warning(
                            f"{extract_error_detail(response)} "
                            "Your job recommendations and match scores are still available."
                        )

                    else:

                        st.error(
                            f"Could not generate explanation: {extract_error_detail(response)}"
                        )

                except requests.exceptions.Timeout:

                    st.warning(
                        "Gemini AI explanation timed out. "
                        "Your job recommendations and match scores are still available—please try again."
                    )

                except requests.exceptions.ConnectionError:

                    st.error(
                        "Could not connect to the backend."
                    )

                except (requests.RequestException, ValueError):

                    st.warning(
                        "Gemini AI could not return an explanation right now. Please try again later."
                    )

        # Display previously generated explanation
        explanation = st.session_state.get(explanation_key)
        explanation_source = st.session_state.get(
            f"{explanation_key}_source",
            "gemini"
        )

        if explanation:

            if explanation_source == "rule_based_fallback":
                st.info(
                    "Gemini AI is temporarily unavailable — showing a rule-based match analysis below."
                )
            else:
                st.markdown(
                    "**🤖 Gemini's Job Match Explanation**"
                )

            st.write(explanation)


# ==================================================
# JOB SEARCH
# ==================================================

st.divider()

st.header("🔎 Search Jobs")

st.write(
    "Search available jobs by keyword and location."
)

with st.form("job_search_form"):

    keyword = st.text_input(
        "Job Keyword",
        placeholder="Example: Python, Java, Machine Learning"
    )

    location = st.text_input(
        "Preferred Location",
        placeholder="Example: Bengaluru, Hyderabad, Remote"
    )

    search_submitted = st.form_submit_button(
        "Search Jobs"
    )


if search_submitted:

    try:
        response = api_request(
            "GET",
            "/api/jobs/search",
            params={
                "keyword": keyword,
                "location": location
            },
            timeout=15
        )

        if response.status_code == 200:

            st.session_state["search_results"] = response.json()

        else:

            st.error(
                f"Search failed: {extract_error_detail(response)}"
            )

    except requests.exceptions.Timeout:

        st.warning("Job search timed out. Please try again.")

    except requests.exceptions.ConnectionError:

        st.error(
            "Could not connect to the backend."
        )

    except (requests.RequestException, ValueError):

        st.error("Job search failed due to an unexpected backend response.")


search_results = st.session_state.get("search_results")

if search_results is not None:

    st.success(
        f"Found {len(search_results)} jobs."
    )

    if not search_results:

        st.info("No jobs matched your search.")

    for job in search_results:

        with st.container(border=True):

            st.subheader(job["title"])

            st.write(
                f"**Company:** {job['company']}"
            )

            st.write(
                f"**Location:** {job['location']}"
            )

            st.write(
                f"**Skills:** {job['required_skills']}"
            )

            st.write(job["description"])

            if job.get("apply_url"):

                st.link_button(
                    "View Application",
                    job["apply_url"]
                )
