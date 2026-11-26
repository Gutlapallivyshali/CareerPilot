
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def rank_jobs(search_query, jobs):

    if not jobs:
        return []

    job_documents = []

    for job in jobs:
        document = f"""
        {job.title}
        {job.company}
        {job.required_skills or ""}
        {job.description or ""}
        {job.location or ""}
        {job.job_type or ""}
        """

        job_documents.append(document)

    vectorizer = TfidfVectorizer(stop_words="english")

    all_documents = [search_query] + job_documents

    tfidf_matrix = vectorizer.fit_transform(all_documents)

    query_vector = tfidf_matrix[0:1]
    job_vectors = tfidf_matrix[1:]

    scores = cosine_similarity(
        query_vector,
        job_vectors
    ).flatten()

    ranked_jobs = []

    for job, score in zip(jobs, scores):
        ranked_jobs.append({
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "required_skills": job.required_skills,
            "description": job.description,
            "match_score": round(float(score) * 100, 2),
            "apply_url": job.apply_url
        })

    ranked_jobs.sort(
        key=lambda job: job["match_score"],
        reverse=True
    )

    return ranked_jobs
