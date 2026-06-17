import json
import csv
import math
from datetime import datetime
from turtle import title

CANDIDATES_FILE = "candidates.jsonl"
OUTPUT_FILE = "submission.csv"

TECH_KEYWORDS = {
    "python": 8,
    "machine learning": 6,
    "ml": 5,
    "deep learning": 5,
    "nlp": 8,
    "natural language processing": 8,
    "llm": 7,
    "transformer": 6,
    "transformers": 6,
    "embedding": 10,
    "embeddings": 10,
    "retrieval": 12,
    "information retrieval": 12,
    "ranking": 12,
    "ranker": 12,
    "recommendation": 12,
    "recommender": 12,
    "search": 10,
    "semantic search": 12,
    "vector search": 12,
    "vector database": 10,
    "faiss": 10,
    "pinecone": 10,
    "qdrant": 10,
    "weaviate": 10,
    "milvus": 10,
    "elasticsearch": 8,
    "opensearch": 8,
    "bm25": 10,
    "xgboost": 6,
    "learning to rank": 12,
    "ndcg": 10,
    "mrr": 10,
    "map": 6,
    "a/b testing": 8,
    "ab testing": 8,
}

BAD_KEYWORDS = {
    "marketing manager": -30,
    "sales": -20,
    "hr manager": -25,
    "recruiter": -15,
    "accountant": -25,
    "graphic designer": -20,
    "only langchain": -15,
    "tutorial": -10,
    "computer vision engineer": -18,
    "computer vision": -12,
    "image classification": -8,
    "speech recognition": -8,
    "junior ml engineer": -10,
    "junior": -8,
}

SERVICE_COMPANIES = [
    "tcs", "infosys", "wipro", "accenture", "cognizant",
    "capgemini", "mindtree", "ltimindtree", "hcl", "tech mahindra"
]

GOOD_LOCATIONS = [
    "pune", "noida", "hyderabad", "mumbai", "delhi", "gurgaon",
    "bengaluru", "bangalore", "india"
]

PROFICIENCY_SCORE = {
    "beginner": 0.25,
    "intermediate": 0.55,
    "advanced": 0.80,
    "expert": 1.00,
}

def safe_lower(x):
    return str(x or "").lower()

def clamp(x, low=0, high=100):
    return max(low, min(high, x))

def text_blob(candidate):
    profile = candidate.get("profile", {})
    parts = [
        profile.get("headline", ""),
        profile.get("summary", ""),
        profile.get("current_title", ""),
        profile.get("current_company", ""),
        profile.get("current_industry", ""),
        profile.get("location", ""),
        profile.get("country", ""),
    ]

    for job in candidate.get("career_history", []):
        parts.extend([
            job.get("title", ""),
            job.get("company", ""),
            job.get("industry", ""),
            job.get("description", ""),
        ])

    for edu in candidate.get("education", []):
        parts.extend([str(v) for v in edu.values()])

    for skill in candidate.get("skills", []):
        parts.append(skill.get("name", ""))

    return safe_lower(" ".join(parts))

def technical_score(candidate, blob):
    score = 0

    for keyword, weight in TECH_KEYWORDS.items():
        if keyword in blob:
            score += weight

    for keyword, penalty in BAD_KEYWORDS.items():
        if keyword in blob:
            score += penalty

    # Skill quality score
    for skill in candidate.get("skills", []):
        name = safe_lower(skill.get("name", ""))
        prof = safe_lower(skill.get("proficiency", "beginner"))
        endorsements = skill.get("endorsements", 0) or 0
        duration = skill.get("duration_months", 0) or 0

        for keyword, weight in TECH_KEYWORDS.items():
            if keyword in name:
                prof_mult = PROFICIENCY_SCORE.get(prof, 0.4)
                duration_mult = min(duration / 48, 1.0)
                endorsement_mult = min(endorsements / 50, 1.0)
                score += weight * prof_mult * (0.6 + 0.25 * duration_mult + 0.15 * endorsement_mult)

    # Strong product signals
    strong_phrases = [
        "built recommendation system",
        "built recommender",
        "designed search",
        "implemented search",
        "ranking system",
        "retrieval pipeline",
        "vector search",
        "semantic search",
        "shipped",
        "production",
        "real users",
        "scale",
    ]
    for phrase in strong_phrases:
        if phrase in blob:
            score += 8

    # Title-based bonus/penalty
    title = safe_lower(candidate.get("profile", {}).get("current_title", ""))

    if any(t in title for t in [
        "senior ai engineer",
        "senior ml engineer",
        "machine learning engineer",
        "nlp engineer",
        "search engineer"
    ]):
        score += 18

    if any(t in title for t in [
        "computer vision",
        "speech",
        "robotics"
    ]):
        score -= 40

    if "junior" in title:
        score -= 28
    return clamp(score)

def experience_score(candidate):
        years = candidate.get("profile", {}).get("years_of_experience", 0) or 0

        if 5 <= years <= 9:
            return 100
        if 4 <= years < 5:
            return 75
        if 9 < years <= 11:
            return 70
        if 3 <= years < 4:
            return 45
        return 25

def product_company_score(candidate, blob):
    profile = candidate.get("profile", {})
    industry = safe_lower(profile.get("current_industry", ""))
    company = safe_lower(profile.get("current_company", ""))

    score = 60

    if any(w in industry for w in ["product", "saas", "software", "internet", "ai", "ml", "marketplace"]):
        score += 25

    if any(w in blob for w in ["startup", "series a", "product company", "marketplace", "platform"]):
        score += 15

    if any(service in company for service in SERVICE_COMPANIES):
        score -= 25

    if "it services" in industry:
        score -= 20

    return clamp(score)

def recency_score(last_active_date):
    try:
        last = datetime.strptime(last_active_date, "%Y-%m-%d")
        reference = datetime(2026, 6, 16)
        days = (reference - last).days
        if days <= 14:
            return 100
        if days <= 30:
            return 85
        if days <= 60:
            return 65
        if days <= 120:
            return 40
        return 15
    except Exception:
        return 30

def behavior_score(candidate):
    s = candidate.get("redrob_signals", {})

    profile_complete = s.get("profile_completeness_score", 0) or 0
    recruiter_response = (s.get("recruiter_response_rate", 0) or 0) * 100
    github_activity = s.get("github_activity_score", 0) or 0
    interview = (s.get("interview_completion_rate", 0) or 0) * 100
    offer = (s.get("offer_acceptance_rate", 0) or 0) * 100
    saved = min((s.get("saved_by_recruiters_30d", 0) or 0) * 10, 100)
    recent = recency_score(s.get("last_active_date", ""))

    verification = 0
    if s.get("verified_email"):
        verification += 35
    if s.get("verified_phone"):
        verification += 35
    if s.get("linkedin_connected"):
        verification += 30

    response_time = s.get("avg_response_time_hours", 999) or 999
    if response_time <= 24:
        response_time_score = 100
    elif response_time <= 72:
        response_time_score = 70
    elif response_time <= 168:
        response_time_score = 40
    else:
        response_time_score = 15

    open_to_work_bonus = 15 if s.get("open_to_work_flag") else -10

    score = (
        profile_complete * 0.10 +
        recruiter_response * 0.20 +
        github_activity * 0.10 +
        interview * 0.15 +
        offer * 0.10 +
        saved * 0.10 +
        recent * 0.10 +
        verification * 0.10 +
        response_time_score * 0.05
    ) + open_to_work_bonus

    return clamp(score)

def availability_score(candidate):
    profile = candidate.get("profile", {})
    s = candidate.get("redrob_signals", {})

    score = 50

    notice = s.get("notice_period_days", 999) or 999
    if notice <= 30:
        score += 25
    elif notice <= 60:
        score += 10
    else:
        score -= 10

    if s.get("willing_to_relocate"):
        score += 15

    location_blob = safe_lower(profile.get("location", "") + " " + profile.get("country", ""))
    if any(loc in location_blob for loc in GOOD_LOCATIONS):
        score += 10

    if s.get("open_to_work_flag"):
        score += 10

    return clamp(score)

def honeypot_penalty(candidate):
    penalty = 0
    years = candidate.get("profile", {}).get("years_of_experience", 0) or 0

    expert_zero_duration = 0
    for skill in candidate.get("skills", []):
        prof = safe_lower(skill.get("proficiency", ""))
        duration = skill.get("duration_months", 0) or 0
        if prof == "expert" and duration == 0:
            expert_zero_duration += 1

    if expert_zero_duration >= 3:
        penalty += 40

    if years < 3:
        blob = text_blob(candidate)
        high_senior_words = ["principal", "staff engineer", "head of ai", "director"]
        if any(w in blob for w in high_senior_words):
            penalty += 30

    return penalty

def make_reason(candidate, score_parts):
    profile = candidate.get("profile", {})
    s = candidate.get("redrob_signals", {})
    blob = text_blob(candidate)

    years = profile.get("years_of_experience", 0)
    title = profile.get("current_title", "Candidate")
    location = profile.get("location", "")

    strengths = []
    concerns = []

    for key in ["retrieval", "ranking", "recommendation", "embeddings", "vector search", "faiss", "pinecone", "nlp", "python"]:
        if key in blob and len(strengths) < 3:
            strengths.append(key)

    if not strengths:
        strengths.append("adjacent AI/data engineering experience")

    notice = s.get("notice_period_days", None)
    response_rate = s.get("recruiter_response_rate", 0) or 0

    if notice and notice > 60:
        concerns.append(f"{notice}-day notice period")
    if response_rate < 0.25:
        concerns.append("low recruiter response rate")
    if not s.get("open_to_work_flag"):
        concerns.append("not marked open to work")

    reason = (
        f"{title} with {years} years of experience in {', '.join(strengths)}; "
        f"location: {location}, recruiter response rate {response_rate:.2f}."
    )

    if concerns:
        reason += " Concern: " + ", ".join(concerns[:2]) + "."

    return reason

def score_candidate(candidate):
    blob = text_blob(candidate)
    title = safe_lower(candidate.get("profile", {}).get("current_title", ""))
    title_penalty = 0

    if "junior" in title:
        title_penalty += 0.08

    if any(x in title for x in ["computer vision", "speech", "robotics"]):
        title_penalty += 0.10

    tech = technical_score(candidate, blob)
    exp = experience_score(candidate)
    product = product_company_score(candidate, blob)
    behavior = behavior_score(candidate)
    availability = availability_score(candidate)
    penalty = honeypot_penalty(candidate)

    final = (
        tech * 0.50 +
        exp * 0.20 +
        product * 0.10 +
        behavior * 0.15 +
        availability * 0.05
    ) - penalty

    final = (clamp(final) / 100) - title_penalty
    final = max(0, final)

    return final, {
        "tech": tech,
        "experience": exp,
        "product": product,
        "behavior": behavior,
        "availability": availability,
        "penalty": penalty,
    }

def main():
    ranked = []
    total = 0

    with open(CANDIDATES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            candidate = json.loads(line)
            total += 1

            score, parts = score_candidate(candidate)
            reason = make_reason(candidate, parts)

            ranked.append({
                "candidate_id": candidate["candidate_id"],
                "score": score,
                "reasoning": reason,
            })

            if total % 10000 == 0:
                print(f"Processed {total} candidates...")

    ranked.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    top100 = ranked[:100]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["candidate_id", "rank", "score", "reasoning"]
        )
        writer.writeheader()

        for i, row in enumerate(top100, start=1):
            writer.writerow({
                "candidate_id": row["candidate_id"],
                "rank": i,
                "score": round(row["score"], 6),
                "reasoning": row["reasoning"],
            })

    print(f"Done. Processed {total} candidates.")
    print(f"Created {OUTPUT_FILE}")

if __name__ == "__main__":
    main()