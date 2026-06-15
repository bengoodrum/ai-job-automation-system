import re
from difflib import SequenceMatcher
import helpers

POSITIVE_KEYWORDS = {
    "project coordinator": 35,
    "technical project coordinator": 35,
    "operations analyst": 35,
    "business analyst": 35,
    "business systems analyst": 35,
    "technical operations analyst": 30,
    "product operations analyst": 30,
    "revenue operations analyst": 30,
    "revops": 30,
    "sales operations analyst": 30,
    "technical support engineer": 30,
    "workflow automation specialist": 30,
    "implementation specialist": 30,
    "data operations analyst": 28,
    "qa analyst": 28,
    "customer success operations": 28,
    "program coordinator": 28,
    "systems coordinator": 25,
    "operations coordinator": 25,
    "analyst": 18,
    "operations": 18,
    "business": 18,
    "implementation": 16,
    "systems": 16,
    "automation": 16,
    "process improvement": 15,
    "workflow": 14,
    "documentation": 12,
    "requirements gathering": 12,
    "stakeholder communication": 14,
    "cross-functional": 14,
    "project support": 14,
    "onboarding": 14,
    "reporting": 14,
    "dashboards": 14,
    "analytics": 14,
    "saas": 12,
    "crm": 14,
    "salesforce": 14,
    "jira": 15,
    "excel": 15,
    "google sheets": 12,
    "python": 12,
    "sql": 14,
    "ai tools": 12,
    "remote": 20,
}

PENALTIES = {
    "senior": -55,
    "manager": -55,
    "director": -55,
    "principal": -55,
    "lead": -55,
    "5+ years": -45,
    "6+ years": -45,
    "7+ years": -45,
    "8+ years": -45,
    "10+ years": -55,
    "construction": -50,
    "recruiting coordinator": -50,
    "warehouse": -50,
    "logistics": -50,
    "event associate": -40,
    "event coordinator": -40,
    "grants coordinator": -40,
    "administrative coordinator": -30,
    "travel coordinator": -40,
    "localization": -40,
    "gaming": -40,
    "healthcare": -40,
    "healthcare staffing": -45,
    "nursing": -45,
    "therapist": -45,
    "social worker": -45,
    "cybersecurity": -45,
    "security analyst": -45,
    "cloud engineer": -45,
    "devops": -45,
    "site reliability": -45,
    "accountant": -45,
    "controller": -45,
    "financial advisor": -45,
    "commission only": -45,
    "door to door": -45,
    "insurance sales": -45,
    "field technician": -45,
    "skilled trades": -45,
    "law enforcement": -45,
    "police": -45,
    "detective": -45,
    "rn": -45,
    "lpn": -45,
    "license required": -25,
    "certification required": -25,
    "pmp": -20,
    "project management professional": -20,
    "cissp": -20,
    "security+": -20,
    "aws certified": -20,
    "ccna": -20,
    "ccnp": -20,
    "cisa": -20,
    "cism": -20,
    "six sigma black belt": -20,
    "six sigma green belt": -20,
    "engineering degree": -20,
    "computer science degree": -20,
    "software engineering degree": -20,
}

WEAK_KEYWORDS = {
    "event": -30,
    "grants": -30,
    "travel": -25,
    "hospitality": -25,
    "recruiting": -25,
    "consultant": -20,
    "engineering": -30,
    "developer": -30,
}

TARGET_ROLES = [
    "project coordinator",
    "technical project coordinator",
    "operations analyst",
    "business analyst",
    "business systems analyst",
    "technical operations analyst",
    "product operations analyst",
    "product operations coordinator",
    "revenue operations analyst",
    "revops associate",
    "sales operations analyst",
    "technical support engineer",
    "workflow automation specialist",
    "implementation specialist",
    "data operations analyst",
    "qa analyst",
    "customer success operations",
    "program coordinator",
    "systems coordinator",
    "operations coordinator",
    "process improvement analyst",
    "ai operations associate",
]

ENTRY_PATTERNS = [
    "0-2 years", "0-1 year", "1-2 years", "entry level",
    "junior", "training provided", "no experience required",
]


# --- Calibrated scoring model -------------------------------------------------
# Goal: a wide distribution rather than everything pinned at 100.
#   95-100 exceptional | 85-94 strong | 70-84 acceptable | 50-69 weak | <50 poor
SCORE_BASE = 45

# Strong, on-target job titles (only the single best match is counted).
EXCEPTIONAL_TITLES = [
    "operations analyst", "business analyst", "business systems analyst",
    "project coordinator", "technical project coordinator", "program coordinator",
    "product operations", "revenue operations", "revops", "sales operations",
    "ai operations", "implementation specialist", "implementation analyst",
    "workflow automation", "technical support engineer", "qa analyst",
    "quality assurance analyst", "data operations analyst",
]
SECONDARY_TITLES = ["analyst", "operations", "coordinator", "associate", "specialist", "business", "support"]

RELEVANT_SKILLS = [
    "python", "sql", "excel", "google sheets", "crm", "salesforce", "jira",
    "reporting", "dashboards", "analytics", "automation", "workflow",
    "process improvement", "onboarding", "api", "saas", "data", "documentation",
    "stakeholder", "cross-functional",
]

SENIOR_TITLE_TERMS = ["senior director", "director", "vp", "vice president", "svp", "evp",
                      "head of", "chief", "principal"]
NURSE_TERMS = ["registered nurse", "nurse", " rn ", "lpn", "clinical", "physician"]
GENERIC_ENGINEER_TITLES = ["software engineer", "data engineer", "devops", "cloud engineer",
                           "backend engineer", "frontend engineer", "ml engineer",
                           "machine learning engineer", "systems engineer", "network engineer"]
FINANCE_TERMS = ["accountant", "controller", "financial analyst", "investment banking",
                 "tax accountant", "auditor", "financial advisor", "cpa required"]
CS_DEGREE_TERMS = ["computer science degree", "cs degree", "degree in computer science",
                   "bs in computer science", "b.s. in computer science"]


def _required_years(text):
    """Largest explicit 'N years' requirement mentioned, else None."""
    years = [int(m) for m in re.findall(r"(\d{1,2})\s*\+?\s*years", text)]
    return max(years) if years else None


def score_job(job, keywords, config=None):
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    location = (job.get("location") or "").lower()
    text = f"{title} {description}"
    match_reasons = []
    red_flags = []
    score = SCORE_BASE

    try:
        salary_min_value = float(job.get("salary_min")) if job.get("salary_min") not in (None, "") else None
    except (TypeError, ValueError):
        salary_min_value = None

    # --- Title fit (single best signal) ---
    title_role = next((role for role in EXCEPTIONAL_TITLES if role in title), None)
    if title_role:
        score += 30
        match_reasons.append(f"On-target role: {title_role}")
    else:
        title_role_desc = next((role for role in EXCEPTIONAL_TITLES if role in description), None)
        secondary = next((t for t in SECONDARY_TITLES if t in title), None)
        if secondary:
            score += 14
            match_reasons.append(f"Related title: {secondary}")
        elif title_role_desc:
            score += 8
            match_reasons.append(f"Target role in description: {title_role_desc}")

    # --- Skill relevance (diminishing returns, capped) ---
    matched_skills = [s for s in RELEVANT_SKILLS if s in text]
    if matched_skills:
        skill_points = min(12, len(matched_skills) * 2)
        score += skill_points
        match_reasons.append("Relevant skills: " + ", ".join(matched_skills[:5]))

    # --- Entry-level / business-ops signals ---
    if any(pattern in text for pattern in ENTRY_PATTERNS):
        score += 5
        match_reasons.append("Entry-level friendly")
    if any(term in text for term in ["cross-functional", "project support", "coordination",
                                     "process improvement", "product operations"]):
        score += 4
        match_reasons.append("Business operations signal")

    # --- Location / remote bonuses ---
    if "hybrid" in text:
        score += 5
        match_reasons.append("Hybrid")
    elif "remote" in text or "work from home" in text:
        score += 8
        match_reasons.append("Remote")
    if "denver" in location or "denver" in text:
        score += 6
        match_reasons.append("Denver area")

    # --- Salary ---
    if salary_min_value is not None:
        if salary_min_value >= 80000:
            score += 6
            match_reasons.append(f"Salary ${salary_min_value:,.0f}")
        elif salary_min_value >= 70000:
            score += 4
            match_reasons.append(f"Salary ${salary_min_value:,.0f}")
        elif salary_min_value < 50000:
            score -= 12
            red_flags.append(f"Low salary ${salary_min_value:,.0f}")

    # --- Experience penalties ---
    req_years = _required_years(text)
    if req_years is not None:
        if req_years >= 7:
            score -= 28
            red_flags.append(f"Requires {req_years}+ years")
        elif req_years >= 5:
            score -= 16
            red_flags.append(f"Requires {req_years} years")
        elif req_years >= 3:
            score -= 8
            red_flags.append(f"Requires {req_years} years")

    # --- Hard penalties ---
    if any(term in title for term in SENIOR_TITLE_TERMS):
        score -= 40
        red_flags.append("Senior/Director/VP level")
    if "manager" in title:
        score -= 20
        red_flags.append("Manager role")
        if req_years is not None and req_years >= 8:
            score -= 20
            red_flags.append("Manager requiring 8+ years")
    if any(term in text for term in NURSE_TERMS):
        score -= 50
        red_flags.append("Nursing/clinical role")
    if "engineer" in title and "technical support engineer" not in title:
        if any(term in text for term in CS_DEGREE_TERMS):
            score -= 40
            red_flags.append("Engineer requiring CS degree")
        elif any(term in title for term in GENERIC_ENGINEER_TITLES):
            score -= 30
            red_flags.append("Engineering role")
    if any(term in text for term in FINANCE_TERMS):
        score -= 30
        red_flags.append("Finance-heavy role")
    if any(term in text for term in helpers.CLEARANCE_DEFENSE_TERMS):
        score -= 50
        red_flags.append("Security clearance required")

    score = max(0, min(100, score))
    priority = "High" if score >= 85 else "Medium" if score >= 70 else "Low"
    return {"score": score, "priority": priority,
            "match_reasons": match_reasons[:6], "red_flags": red_flags[:4]}


def score_jobs(jobs, keywords, config=None):
    scored_jobs = []
    for job in jobs:
        result = score_job(job, keywords, config=config)
        job_copy = {
            **job,
            "score": result["score"],
            "priority": result["priority"],
            "match_reasons": result["match_reasons"],
            "red_flags": result["red_flags"],
            "fit_reasons": result["match_reasons"],
            "concerns": result["red_flags"],
        }
        scored_jobs.append(job_copy)
    return sorted(scored_jobs, key=lambda x: x["score"], reverse=True)


def parse_salary_min(job):
    salary_min = job.get("salary_min")
    if salary_min in (None, ""):
        return None
    try:
        return float(salary_min)
    except (TypeError, ValueError):
        return None


def classify_role_category(job):
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    text = f"{title} {description}"
    for term in helpers.NEW_ROLE_CATEGORIES["japan_apac"]:
        if term in text:
            if any(x in text for x in ["localization", "localization specialist"]):
                return "localization"
            return "japan_apac"
    if any(term in text for term in helpers.NEW_ROLE_CATEGORIES["international_ops"]):
        return "international_ops"
    if any(term in text for term in helpers.NEW_ROLE_CATEGORIES["localization"]):
        return "localization"
    if any(term in text for term in helpers.NEW_ROLE_CATEGORIES["gaming_entertainment"]):
        return "gaming_entertainment"
    if any(term in text for term in helpers.NEW_ROLE_CATEGORIES["music_events"]):
        return "music_events"
    if any(term in text for term in helpers.NEW_ROLE_CATEGORIES["travel_tech"]):
        return "travel_tech"
    if any(term in title for term in helpers.CUSTOMER_SUCCESS_TERMS):
        return "customer_success"
    if any(term in title for term in helpers.TECH_ADJACENT_TITLE_TERMS):
        return "tech_adjacent"
    if any(term in title for term in helpers.ANALYST_TERMS):
        return "analyst"
    tech_signal_terms = ["python", "sql", "api", "automation", "ai", "workflow", "data", "crm", "saas", "implementation", "reporting", "process improvement"]
    if any(term in text for term in tech_signal_terms):
        return "tech_adjacent"
    if any(term in title for term in helpers.CORPORATE_OPS_TERMS):
        return "corporate_ops"
    return "corporate_ops"


def build_tech_fit_reason(job):
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    text = f"{title} {description}"
    matches = [term for term in helpers.TECH_FIT_TERMS if term in text]
    if matches:
        return "Tech fit via " + ", ".join(sorted(set(matches)))
    if "customer success" in text or "client success" in text:
        return "Fits customer-facing operations and support work"
    return "Business operations background with strong coordination and process focus"


def calculate_realistic_fit_score(job, resume_data, config):
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    text = f"{title} {description}"
    salary_min = parse_salary_min(job)
    score = 0
    if any(pattern in text for pattern in helpers.EXPERIENCE_PATTERNS):
        score += 35
    if any(word in title for word in helpers.PREFER_TITLE_WORDS):
        score += 25
    if any(term in text for term in ["operations", "business", "implementation", "workflow", "automation", "process improvement", "coordination", "crm", "salesforce", "jira", "reporting", "dashboards", "analytics", "onboarding"]):
        score += 20
    if any(term in text for term in ["remote", "hybrid", "work from home"]):
        score += 15
    for keyword in resume_data.get("keywords", [])[:3]:
        if keyword.lower() in text:
            score += 10
    min_salary = config.get("min_salary", 60000)
    ideal_salary = config.get("ideal_salary", 70000)
    if salary_min and salary_min >= ideal_salary:
        score += 15
    elif salary_min and salary_min >= min_salary:
        score += 10
    if score >= 100:
        return 100
    return score


def calculate_stretch_level(job, resume_data, config):
    description = (job.get("description") or "").lower()
    salary_min = parse_salary_min(job)
    stretch_signals = 0
    if any(pattern in description for pattern in helpers.EXPERIENCE_SKIP_PATTERNS):
        stretch_signals += 2
    if any(pattern in description for pattern in helpers.EXPERIENCE_APPLY_PATTERNS):
        stretch_signals -= 1
    min_salary = config.get("min_salary", 60000)
    if salary_min and salary_min < min_salary:
        stretch_signals += 1
    if ("japan" in description or "apac" in description) and any(pattern in description for pattern in helpers.EXPERIENCE_SKIP_PATTERNS):
        stretch_signals += 1
    if stretch_signals >= 2:
        return "High"
    if stretch_signals >= 1:
        return "Medium"
    return "Low"


def determine_next_skill_to_learn(job, resume_data):
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    text = f"{title} {description}"
    resume_skills_lower = [s.lower() for s in resume_data.get("skills", [])]
    suggested_skills = [
        ("Japanese language basics", ["japan", "tokyo", "japanese"]),
        ("Project management tools", ["asana", "monday", "jira", "project management"]),
        ("Data analysis", ["data", "analytics", "excel", "sql"]),
        ("CRM systems", ["crm", "salesforce", "hubspot"]),
        ("No-code automation", ["automation", "zapier", "workflow", "airtable"]),
        ("Localization best practices", ["localization", "translation", "internationalization"]),
        ("Gaming industry knowledge", ["gaming", "esports", "game"]),
        ("Event coordination", ["event", "conference", "summit"]),
        ("API/Integration knowledge", ["api", "integration", "webhook"]),
    ]
    for skill_name, keywords in suggested_skills:
        if any(keyword in text for keyword in keywords) and skill_name.lower() not in resume_skills_lower:
            return skill_name
    return "Project management tools"


def determine_salary_status(job, config):
    salary_min = parse_salary_min(job)
    if salary_min is None:
        return "unknown"
    if salary_min >= config.get("ideal_salary", 70000):
        return "above_ideal"
    if salary_min >= config.get("min_salary", 60000):
        return "above_minimum"
    return "below_minimum"


def determine_should_apply(interview_probability, experience_requirement, score):
    if experience_requirement == "Skip":
        return "No"
    if interview_probability == "High" and experience_requirement in ["Apply", "Maybe"]:
        return "Apply" if experience_requirement == "Apply" else "Maybe"
    if interview_probability == "Medium" and experience_requirement == "Apply":
        return "Apply"
    if interview_probability == "Medium" and experience_requirement == "Maybe":
        return "Maybe"
    if interview_probability == "Low" and experience_requirement == "Apply" and score >= 70:
        return "Apply"
    if experience_requirement == "Apply" and score >= 60:
        return "Apply"
    if experience_requirement == "Maybe" and score >= 50:
        return "Maybe"
    return "No"


def classify_experience_requirement(job, config=None):
    description = (job.get("description") or "").lower()
    title = (job.get("title") or "").lower()
    if any(pattern in description for pattern in helpers.EXPERIENCE_SKIP_PATTERNS):
        return "Skip"
    if any(pattern in description for pattern in helpers.EXPERIENCE_APPLY_PATTERNS):
        return "Apply"
    if any(pattern in description for pattern in helpers.EXPERIENCE_MAYBE_PATTERNS):
        return "Maybe"
    return "Apply"


def calculate_interview_probability(job, resume_data, score):
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    text = f"{title} {description}"
    salary_min = parse_salary_min(job)
    has_preferred_title = any(word in title for word in helpers.PREFER_TITLE_WORDS)
    has_entry_exp = any(pattern in description for pattern in ENTRY_PATTERNS)
    has_remote = any(term in text for term in ["remote", "hybrid", "work from home"])
    has_ops_signal = any(term in title for term in ["operations", "business", "analyst", "coordinator", "associate", "specialist", "support"])
    high_salary = salary_min and salary_min >= 75000
    signals = 0
    if has_preferred_title:
        signals += 1
    if has_entry_exp:
        signals += 1
    if has_remote:
        signals += 1
    if has_ops_signal:
        signals += 1
    if salary_min is not None:
        signals += 1
    if high_salary:
        signals += 1
    if score >= 100:
        signals += 1
    reasons = []
    if has_preferred_title:
        reasons.append("coordinator/assistant title")
    if has_entry_exp:
        reasons.append("entry-level position")
    if has_remote:
        reasons.append("remote/hybrid role")
    if has_ops_signal:
        reasons.append("operations/business title signal")
    if high_salary:
        reasons.append(f"${salary_min:,.0f} salary")
    if score >= 100:
        reasons.append("strong match")
    if signals >= 3:
        probability = "High"
    elif signals >= 2:
        probability = "Medium"
    else:
        probability = "Low"
    reason = ", ".join(reasons) if reasons else "matches your skills"
    return probability, reason
