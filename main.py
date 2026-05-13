#!/usr/bin/env python3
"""
Job Search Assistant - A beginner-friendly job scoring tool with REAL job listings
Fetches jobs from Adzuna API
"""

import yaml
import csv
import re
import requests
from pathlib import Path
from datetime import datetime
from fpdf import FPDF

APPLIED_JOBS_FILE = "applied_jobs.csv"
SEEN_JOBS_FILE = "seen_jobs.csv"

# Adzuna API constants
ADZUNA_API_BASE = "https://api.adzuna.com/v1/api/jobs"

# Filtering constants
EXCLUDE_TITLE_WORDS = ["senior", "manager", "director", "lead", "principal"]
PREFER_TITLE_WORDS = ["coordinator", "assistant", "associate", "entry level"]
EXCLUDE_TECHNICAL_ROLES = [
    "software engineer", "data scientist", "developer", "scientist",
    "staff engineer", "principal engineer", "machine learning engineer",
    "full stack developer", "backend engineer", "frontend engineer",
    "devops engineer", "kubernetes", "cloud architecture",
]
EXPERIENCE_PATTERNS = ["0-2 years", "entry level", "junior", "0-1 year", "1-2 years", "no experience required"]

SKIP_APPLIED_PATTERNS = [
    "fmi", "j.e. dunn", "insight global", "commonspirit",
    "govcio", "cbre", "kharon", "subaru",
]

TECH_FIT_TERMS = [
    "python", "sql", "api", "automation", "ai", "workflow", "data",
    "crm", "saas", "implementation", "support", "operations",
    "reporting", "process improvement",
]
TECH_ADJACENT_TITLE_TERMS = [
    "operations analyst", "business systems analyst", "technical project coordinator",
    "technical operations coordinator", "revenue operations associate", "sales operations analyst",
    "ai operations associate", "implementation specialist",
    "customer success engineer", "solutions coordinator", "product operations associate",
    "workflow automation specialist", "data operations associate", "junior business analyst",
    "technical support engineer", "qa analyst", "automation specialist",
    "no-code automation specialist",
]
CUSTOMER_SUCCESS_TERMS = ["customer success", "client success", "support engineer", "support specialist"]
ANALYST_TERMS = ["analyst", "business analyst", "operations analyst", "sales operations analyst", "data operations associate"]
CORPORATE_OPS_TERMS = ["coordinator", "associate", "administrative", "operations", "assistant"]

EXPERIENCE_APPLY_PATTERNS = [
    "0-2 years", "0-1 year", "1-2 years", "entry level",
    "junior", "training provided", "no experience required",
    "coordinator", "associate", "assistant",
]
EXPERIENCE_MAYBE_PATTERNS = [
    "support", "operations", "administrative", "office", "customer success",
    "program", "project", "client", "account",
]
EXPERIENCE_SKIP_PATTERNS = [
    "3+ years", "3 years", "4 years", "5 years", "6 years", "7 years",
    "8 years", "9 years", "10 years", "experience required", "specialized experience required",
    "legal experience required", "investment banking experience required",
]

# Search parameters for entry-level business/operations/admin roles
TARGET_KEYWORDS = [
    "operations coordinator",
    "administrative coordinator",
    "project coordinator",
    "program coordinator",
    "sales operations coordinator",
    "revenue operations coordinator",
    "business operations associate",
    "customer success associate",
    "client success associate",
    "account coordinator",
    "recruiting coordinator",
    "hr coordinator",
    "office operations coordinator",
    "operations analyst",
    "business systems analyst",
    "technical project coordinator",
    "technical operations coordinator",
    "revenue operations associate",
    "sales operations analyst",
    "ai operations associate",
    "implementation specialist",
    "customer success engineer entry level",
    "solutions coordinator",
    "product operations associate",
    "workflow automation specialist",
    "data operations associate",
    "junior business analyst",
    "technical support engineer",
    "qa analyst",
    "automation specialist",
    "no-code automation specialist",
]

# Target roles for application planning
TARGET_ROLES = [
    "operations coordinator",
    "administrative coordinator",
    "project coordinator",
    "program coordinator",
    "sales operations coordinator",
    "revenue operations coordinator",
    "business operations associate",
    "operations analyst",
    "business systems analyst",
    "technical project coordinator",
    "technical operations coordinator",
    "sales operations analyst",
    "ai operations associate",
    "implementation specialist",
    "product operations associate",
    "workflow automation specialist",
    "data operations associate",
    "junior business analyst",
    "customer success associate",
    "client success associate",
    "solutions coordinator",
]
SKILL_TERMS = [
    "excel", "google sheets", "data entry", "project coordination", "communication",
    "organization", "workflow", "scheduling", "customer service", "presentation",
    "team support", "administrative support", "event planning", "social media",
    "analysis", "reporting", "calendar management"
]

TITLE_TERMS = [
    "operations coordinator", "administrative coordinator", "project coordinator",
    "marketing coordinator", "business analyst", "customer success associate",
    "event coordinator", "music industry coordinator", "assistant", "specialist"
]

RESUME_KEYWORD_TERMS = SKILL_TERMS + TITLE_TERMS + [
    "remote", "entry-level", "junior", "manager", "liaison", "support"
]

# Japan/APAC specific scoring boosts
JAPAN_APAC_BOOST_TERMS = [
    "japan", "japanese", "tokyo", "apac", "asia-pacific", "international",
    "global", "localization", "gaming", "music", "events", "creator",
    "travel", "tourism", "partnerships", "saas", "operations", "workflow",
    "automation"
]

NEW_ROLE_CATEGORIES = {
    "japan_apac": ["japan", "apac", "asia-pacific", "tokyo"],
    "international_ops": ["international", "global", "worldwide"],
    "localization": ["localization", "localization specialist", "localization coordinator"],
    "gaming_entertainment": ["gaming", "game", "esports"],
    "music_events": ["music", "event", "events", "creator"],
    "travel_tech": ["travel", "tourism", "travel operations"],
    "tech_adjacent": TECH_ADJACENT_TITLE_TERMS,
    "corporate_ops": CORPORATE_OPS_TERMS,
}


def load_config(config_file="config.yaml"):
    """Load configuration from YAML file and merge defaults."""
    defaults = {
        "daily_target_results": 20,
        "min_salary": 60000,
        "ideal_salary": 70000,
        "max_experience_years": 2,
        "allow_seen_jobs": False,
        "keywords": TARGET_KEYWORDS,
        "target_roles": TARGET_KEYWORDS,
        "exclude_keywords": [
            "senior", "director", "manager", "commission only",
            "door to door", "insurance sales", "independent contractor",
            "unpaid", "rn", "nurse", "clinical", "physician",
            "medical license", "legal experience required", "investment banking experience required",
        ],
        "results_per_search": 50,
        "locations": ["Denver, CO", "remote"],
        "preferences": {
            "min_score": 50,
            "max_results": 50,
        },
    }

    try:
        with open(config_file, "r") as f:
            loaded = yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"Error: {config_file} not found!")
        loaded = {}

    config = {**defaults, **loaded}
    if loaded.get("preferences"):
        config["preferences"] = {**defaults["preferences"], **loaded.get("preferences", {})}

    # Normalize enabled config lists
    config["keywords"] = [kw for kw in (config.get("keywords") or []) if kw]
    config["target_roles"] = [role for role in (config.get("target_roles") or []) if role]
    config["exclude_keywords"] = [kw.lower() for kw in (config.get("exclude_keywords") or []) if kw]
    return config


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_resume_data(resume_file="resume.txt"):
    """Extract keywords, skills, and job titles from resume text"""
    try:
        with open(resume_file, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Warning: {resume_file} not found. Resume extraction skipped.")
        return {
            "keywords": [],
            "skills": [],
            "titles": []
        }

    normalized = normalize_text(text)

    found_skills = [skill for skill in SKILL_TERMS if skill in normalized]
    found_titles = [title for title in TITLE_TERMS if title in normalized]
    found_keywords = [keyword for keyword in RESUME_KEYWORD_TERMS if keyword in normalized]

    # Keep unique and ordered results
    keywords = list(dict.fromkeys(found_keywords))[:12]
    skills = list(dict.fromkeys(found_skills))[:8]
    titles = list(dict.fromkeys(found_titles))[:6]

    if not keywords:
        keywords = ["operations", "administrative", "coordination"]
    if not skills:
        skills = ["communication", "organization", "team support"]
    if not titles:
        titles = ["operations coordinator", "assistant", "coordinator"]

    return {
        "keywords": keywords,
        "skills": skills,
        "titles": titles,
        "full_text": normalized,
    }


def filter_jobs(jobs, config=None):
    """Filter jobs based on config keywords and exclude criteria"""
    filtered = []
    
    # Get config lists
    keywords = []
    if config and config.get("keywords"):
        keywords = [kw.lower() for kw in config.get("keywords", [])]
    
    exclude_keywords = []
    if config and config.get("exclude_keywords"):
        exclude_keywords = [kw.lower() for kw in config.get("exclude_keywords", [])]
    
    min_salary = config.get("min_salary") if config else None
    include_healthcare = config.get("include_healthcare", False) if config else False
    
    for job in jobs:
        title = job.get("title", "").lower()
        description = job.get("description", "").lower()
        salary_min = job.get("salary_min")
        text = f"{title} {description}"

        # Skip healthcare unless explicitly included
        healthcare_terms = ["clinical", "nurse", "rn", "prn", "physician", "medical", "healthcare"]
        if not include_healthcare and any(term in title for term in healthcare_terms):
            continue

        # Skip if contains exclude keywords
        if any(keyword in text for keyword in exclude_keywords):
            continue

        # Skip if contains EXCLUDE_TITLE_WORDS or EXCLUDE_TECHNICAL_ROLES (from constants)
        if any(word in title for word in EXCLUDE_TITLE_WORDS):
            continue
        if any(role in title for role in EXCLUDE_TECHNICAL_ROLES):
            continue
        
        # Skip jobs below min_salary if salary is known
        if min_salary and salary_min:
            try:
                if float(salary_min) < min_salary:
                    continue
            except (TypeError, ValueError):
                pass

        # MAIN CHECK: Keep if job contains ANY of the config keywords
        # OR has preferred title words (coordinator, assistant, associate)
        # OR mentions entry-level experience
        has_keyword_match = any(keyword in text for keyword in keywords) if keywords else False
        has_preferred = any(word in title for word in PREFER_TITLE_WORDS)
        has_entry_exp = any(pattern in description for pattern in EXPERIENCE_PATTERNS)

        # Keep job if it matches any of these criteria
        if has_keyword_match or has_preferred or has_entry_exp:
            job_id = generate_job_id(job.get("company"), job.get("title"))
            job["job_id"] = job_id
            filtered.append(job)

    return filtered


def normalize_match_key(value):
    """Normalize text for matching: lowercase, remove punctuation, collapse spaces"""
    if not value:
        return ""
    # Remove punctuation and special characters
    text = re.sub(r'[^\w\s]', '', value)
    # Collapse multiple spaces and strip
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower()


def generate_job_id(company, title):
    """Generate a stable job_id from company and title with thorough normalization"""
    if not company or not title:
        return ""
    
    # Normalize company and title
    company_norm = company.lower().strip()
    title_norm = title.lower().strip()
    
    # Remove parentheses and their contents
    company_norm = re.sub(r'\([^)]*\)', '', company_norm)
    title_norm = re.sub(r'\([^)]*\)', '', title_norm)
    
    # Remove punctuation (keep spaces and alphanumeric)
    company_norm = re.sub(r'[^\w\s]', '', company_norm)
    title_norm = re.sub(r'[^\w\s]', '', title_norm)
    
    # Remove specific words
    words_to_remove = ['remote', 'hybrid', 'i', 'ii', 'iii', 'iv', 'v', 'senior', 'junior', 'entry', 'level']
    for word in words_to_remove:
        company_norm = re.sub(r'\b' + word + r'\b', '', company_norm)
        title_norm = re.sub(r'\b' + word + r'\b', '', title_norm)
    
    # Collapse multiple spaces and strip
    company_norm = re.sub(r'\s+', ' ', company_norm).strip()
    title_norm = re.sub(r'\s+', ' ', title_norm).strip()
    
    # Create job_id as company_title (underscore separated)
    job_id = f"{company_norm}_{title_norm}".replace(' ', '_')
    return job_id


def normalize_link(value):
    return (value or "").strip().lower()


def load_applied_jobs(applied_file=APPLIED_JOBS_FILE):
    """Load applied jobs and return a list of normalized company/title/link entries."""
    path = Path(applied_file)
    if not path.exists():
        return []

    applied = []
    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                company_norm = normalize_match_key(row.get("company", ""))
                title_norm = normalize_match_key(row.get("title", ""))
                link_norm = normalize_link(row.get("link", ""))
                if company_norm or title_norm or link_norm:
                    applied.append({"company": company_norm, "title": title_norm, "link": link_norm})
    except Exception as e:
        print(f"⚠️  Error loading applied jobs: {e}")
        return []
    return applied


def load_seen_jobs(seen_file=SEEN_JOBS_FILE):
    """Load seen jobs history and return normalized company/title/link entries."""
    path = Path(seen_file)
    if not path.exists():
        return []

    seen = []
    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                company_norm = normalize_match_key(row.get("company", ""))
                title_norm = normalize_match_key(row.get("title", ""))
                link_norm = normalize_link(row.get("link", ""))
                if company_norm or title_norm or link_norm:
                    seen.append({"company": company_norm, "title": title_norm, "link": link_norm})
    except Exception as e:
        print(f"⚠️  Error loading seen jobs: {e}")
        return []
    return seen


def entry_matches_job(entry, company_norm, title_norm, link_norm):
    if entry.get("link") and link_norm and entry["link"] == link_norm:
        return True
    if entry.get("company") and entry["company"] in company_norm:
        return True
    if entry.get("title") and entry["title"] in title_norm:
        return True
    return False


def is_applied_or_excluded(job, applied_entries):
    """Check if a job should be skipped because it matches applied history or blocked names."""
    job_company = (job.get("company") or "").lower()
    job_title = (job.get("title") or "").lower()
    job_link = normalize_link(job.get("link", ""))
    if not job_company and not job_title and not job_link:
        return False

    # Skip any unwanted company/title patterns regardless of applied history
    if any(block in job_company or block in job_title for block in SKIP_APPLIED_PATTERNS):
        return True

    job_company_norm = normalize_match_key(job_company)
    job_title_norm = normalize_match_key(job_title)

    for applied in applied_entries:
        if entry_matches_job(applied, job_company_norm, job_title_norm, job_link):
            return True
    return False


def filter_applied_jobs(jobs, applied_entries):
    """Exclude jobs already applied to or filtered by blocked names."""
    filtered = []
    skipped_count = 0
    for job in jobs:
        if is_applied_or_excluded(job, applied_entries):
            skipped_count += 1
            continue
        filtered.append(job)
    return filtered, skipped_count


def is_seen_or_excluded(job, seen_entries, allow_seen=False):
    """Check if a job should be skipped because it has been seen before."""
    if allow_seen:
        return False

    job_company = (job.get("company") or "").lower()
    job_title = (job.get("title") or "").lower()
    job_link = normalize_link(job.get("link", ""))
    if not job_company and not job_title and not job_link:
        return False

    job_company_norm = normalize_match_key(job_company)
    job_title_norm = normalize_match_key(job_title)

    for seen in seen_entries:
        if entry_matches_job(seen, job_company_norm, job_title_norm, job_link):
            return True
    return False


def filter_seen_jobs(jobs, seen_entries, allow_seen=False):
    """Exclude previously seen jobs unless configuration allows them."""
    filtered = []
    skipped_count = 0
    for job in jobs:
        if is_seen_or_excluded(job, seen_entries, allow_seen=allow_seen):
            skipped_count += 1
            continue
        filtered.append(job)
    return filtered, skipped_count


def filter_duplicates(jobs):
    """Remove duplicate jobs within the same run based on job_id."""
    seen = set()
    filtered = []
    skipped_count = 0
    for job in jobs:
        job_id = job.get("job_id")
        if job_id not in seen:
            seen.add(job_id)
            filtered.append(job)
        else:
            skipped_count += 1
    return filtered, skipped_count


def build_target_role_list(config):
    if config and config.get("target_roles"):
        return config.get("target_roles")
    return TARGET_ROLES


def build_resume_bullets(job, resume_data):
    skills = resume_data.get("skills", [])
    titles = resume_data.get("titles", [])
    bullets = []

    if skills:
        bullets.append(f"Applied strong {skills[0]} skills to support team operations and coordination.")
    if len(skills) > 1:
        bullets.append(f"Used {skills[1]} and {skills[2] if len(skills) > 2 else 'organizational'} abilities to manage scheduling and communication.")
    if titles:
        bullets.append(f"Delivered reliable work in support roles such as {titles[0]} and {titles[1] if len(titles) > 1 else 'assistant'} positions.")

    return bullets[:3]


def build_short_message(job, resume_data):
    title = job.get("title", "this role")
    company = job.get("company", "Hiring team")
    skills = resume_data.get("skills", [])
    titles = resume_data.get("titles", [])

    skill_phrase = ", ".join(skills[:3]) if skills else "strong organizational skills"
    title_phrase = titles[0] if titles else "coordination"
    greeting = f"Hi {company}," if company and company.lower() != "your team" else "Hi Hiring team,"

    return (
        f"{greeting}\n\n"
        f"I’m very interested in the {title}. With experience in {skill_phrase}, I’m confident I can help your team stay organized, keep projects moving, and support day-to-day operations effectively. "
        f"I’ve previously worked in {title_phrase} and administrative support roles, where I improved communication and helped teams meet deadlines.\n\n"
        "If you’re available for a quick 10-minute chat, I’d love to explain how I can contribute to this role and deliver value immediately."
    )


def classify_role_category(job):
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    text = f"{title} {description}"
    
    # Check for Japan/APAC roles
    if any(term in text for term in NEW_ROLE_CATEGORIES["japan_apac"]):
        if any(term in text for term in ["localization", "localization specialist"]):
            return "localization"
        return "japan_apac"
    
    # Check for international operations
    if any(term in text for term in NEW_ROLE_CATEGORIES["international_ops"]):
        return "international_ops"
    
    # Check for localization roles
    if any(term in text for term in NEW_ROLE_CATEGORIES["localization"]):
        return "localization"
    
    # Check for gaming/entertainment
    if any(term in text for term in NEW_ROLE_CATEGORIES["gaming_entertainment"]):
        return "gaming_entertainment"
    
    # Check for music/events
    if any(term in text for term in NEW_ROLE_CATEGORIES["music_events"]):
        return "music_events"
    
    # Check for travel/tourism
    if any(term in text for term in NEW_ROLE_CATEGORIES["travel_tech"]):
        return "travel_tech"
    
    # Check for customer success
    if any(term in title for term in CUSTOMER_SUCCESS_TERMS):
        return "customer_success"
    
    # Check for tech-adjacent roles
    if any(term in title for term in TECH_ADJACENT_TITLE_TERMS):
        return "tech_adjacent"
    
    # Check for analyst roles
    if any(term in title for term in ANALYST_TERMS):
        return "analyst"
    
    # Check for tech signals in description
    tech_signal_terms = [
        "python", "sql", "api", "automation", "ai", "workflow",
        "data", "crm", "saas", "implementation", "reporting",
        "process improvement",
    ]
    if any(term in text for term in tech_signal_terms):
        return "tech_adjacent"
    
    # Default to corporate ops
    if any(term in title for term in CORPORATE_OPS_TERMS):
        return "corporate_ops"
    return "corporate_ops"


def calculate_japan_connection(job, role_category):
    """Calculate Japan/APAC connection strength (0-100)"""
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    text = f"{title} {description}"
    
    score = 0
    
    # Direct Japan/APAC mentions
    if any(term in text for term in ["japan", "tokyo", "japanese"]):
        score += 40
    if any(term in text for term in ["apac", "asia-pacific", "asia pacific"]):
        score += 35
    
    # International/global mentions
    if any(term in text for term in ["international", "global"]):
        score += 20
    
    # Industry signals
    if any(term in text for term in ["localization", "gaming", "music", "events"]):
        score += 15
    
    # Role category bonus
    if role_category in ["japan_apac", "international_ops", "localization"]:
        score += 25
    
    return min(100, score)


def calculate_travel_potential(job, role_category):
    """Estimate likelihood this role could lead to Japan/APAC travel (0-100)"""
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    text = f"{title} {description}"
    
    score = 0
    
    # Direct travel signals
    if any(term in text for term in ["travel", "relocation", "international", "global"]):
        score += 30
    
    # Remote/hybrid = more travel potential
    if any(term in text for term in ["remote", "hybrid", "flexible"]):
        score += 15
    
    # Partnership/events roles often travel
    if any(term in text for term in ["partnerships", "events", "creator"]):
        score += 20
    
    # Role category signals
    if role_category in ["japan_apac", "international_ops", "travel_tech", "gaming_entertainment"]:
        score += 25
    
    # Coordination roles are more likely to travel for events/partnerships
    if any(term in text for term in ["coordinator", "specialist", "associate"]):
        score += 10
    
    return min(100, score)


def calculate_realistic_fit_score(job, resume_data, config):
    """Calculate how realistic this job is given experience level and skills"""
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    salary_min = parse_salary_min(job)
    
    score = 0
    
    # Entry-level experience signals
    if any(pattern in description for pattern in EXPERIENCE_PATTERNS):
        score += 35
    
    # Preferred title terms
    if any(word in title for word in PREFER_TITLE_WORDS):
        score += 30
    
    # Resume skill match
    resume_keywords = resume_data.get("keywords", [])
    for keyword in resume_keywords[:3]:  # Top 3 keywords
        if keyword.lower() in description or keyword.lower() in title:
            score += 15
    
    # Salary alignment
    min_salary = config.get("min_salary", 60000)
    ideal_salary = config.get("ideal_salary", 70000)
    if salary_min and salary_min >= ideal_salary:
        score += 15
    elif salary_min and salary_min >= min_salary:
        score += 10
    
    return min(100, score)


def determine_why_moves_toward_japan(job, role_category, japan_connection):
    """Generate explanation of how this role moves you toward Japan/APAC opportunities"""
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    text = f"{title} {description}"
    
    reasons = []
    
    if japan_connection >= 40:
        if "japan" in text or "tokyo" in text:
            reasons.append("Direct Japan/APAC focus")
        if "apac" in text or "asia-pacific" in text:
            reasons.append("APAC region responsibility")
    
    if "localization" in text:
        reasons.append("Localization experience valuable for international expansion")
    
    if "gaming" in text or "music" in text or "events" in text:
        reasons.append("Global entertainment industry connections")
    
    if "international" in text or "global" in text:
        reasons.append("International operations background")
    
    if "operations" in text or "coordinator" in text:
        reasons.append("Operations/coordination skills transfer globally")
    
    if "partnerships" in text or "creator" in text:
        reasons.append("Partnership/creator network potential")
    
    if not reasons:
        reasons.append("Entry-level operations role with growth potential")
    
    return " | ".join(reasons[:2])  # Top 2 reasons


def calculate_stretch_level(job, resume_data, config):
    """Determine if this is Low/Medium/High stretch for user"""
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    salary_min = parse_salary_min(job)
    
    stretch_signals = 0
    
    # Experience requirement signals
    if any(pattern in description for pattern in EXPERIENCE_SKIP_PATTERNS):
        stretch_signals += 2
    if any(pattern in description for pattern in EXPERIENCE_APPLY_PATTERNS):
        stretch_signals -= 1
    
    # Salary signals
    min_salary = config.get("min_salary", 60000)
    if salary_min and salary_min < min_salary:
        stretch_signals += 1
    
    # Japan/international without experience signals
    if ("japan" in description or "apac" in description) and any(pattern in description for pattern in EXPERIENCE_SKIP_PATTERNS):
        stretch_signals += 1
    
    if stretch_signals >= 2:
        return "High"
    elif stretch_signals >= 1:
        return "Medium"
    else:
        return "Low"


def determine_next_skill_to_learn(job, resume_data):
    """Recommend next skill to develop for this role"""
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    text = f"{title} {description}"
    
    # Resume skills for comparison
    resume_skills = resume_data.get("skills", [])
    resume_skills_lower = [s.lower() for s in resume_skills]
    
    # Suggested skills in priority order
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
        if any(keyword in text for keyword in keywords):
            if skill_name.lower() not in resume_skills_lower:
                return skill_name
    
    return "Project management tools"


def build_tech_fit_reason(job):
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    text = f"{title} {description}"
    matches = [term for term in TECH_FIT_TERMS if term in text]
    if matches:
        return "Tech fit via " + ", ".join(sorted(set(matches)))
    if "customer success" in text or "client success" in text:
        return "Fits customer-facing operations and support work"
    return "Business operations background with strong coordination and process focus"


def build_reason_and_priority(job, resume_data, target_roles):
    title = job.get("title", "").lower()
    description = job.get("description", "").lower()
    score = job.get("score", 0)

    title_match = any(role in title for role in target_roles)
    strong_keyword_match = any(keyword in description or keyword in title for keyword in resume_data.get("keywords", []))
    
    # Check for preferred terms and entry-level
    has_preferred_title = any(word in title for word in PREFER_TITLE_WORDS)
    has_entry_exp = any(pattern in description for pattern in EXPERIENCE_PATTERNS)

    if score >= 100 and (has_preferred_title or has_entry_exp):
        return "High", "Excellent match: entry-level role with preferred title terms. Strong candidate for immediate application."
    if score >= 70 and title_match:
        return "High", "Strong match: title aligns with target roles and scoring indicates good fit."
    if score >= 50:
        return "Medium", "Good fit: role matches several skills and preferences. Review job details carefully."
    if score >= 30 and strong_keyword_match:
        return "Medium", "Reasonable match with resume skills, but may need tailoring. Consider if experience level fits."
    return "Low", "Lower fit: role may not align with entry-level preferences or target roles. Use for networking only."


def calculate_interview_probability(job, resume_data, score):
    """
    Calculate interview probability based on job fit, salary, and resume match.
    Returns: (probability_level, reason_to_apply)
    """
    title = job.get("title", "").lower()
    description = job.get("description", "").lower()
    salary_min = job.get("salary_min")
    
    # Criteria
    has_preferred_title = any(word in title for word in PREFER_TITLE_WORDS)
    has_entry_exp = any(pattern in description for pattern in EXPERIENCE_PATTERNS)
    high_salary = salary_min and salary_min >= 75000 if salary_min else False
    
    # Count positive signals
    signals = 0
    if has_preferred_title:
        signals += 1
    if has_entry_exp:
        signals += 1
    if salary_min:
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
    if high_salary:
        reasons.append(f"${salary_min:,.0f} salary")
    if score >= 100:
        reasons.append("strong match")
    
    # Determine probability level
    if signals >= 3:
        probability = "High"
    elif signals >= 2:
        probability = "Medium"
    else:
        probability = "Low"
    
    reason = ", ".join(reasons) if reasons else "matches your skills"
    return probability, reason


def clean_filename(text):
    """Remove unsafe filename characters"""
    # Replace spaces and special characters
    text = re.sub(r"[/\\:*?\"<>|(),]", "", text)
    # Replace multiple spaces with single space
    text = re.sub(r"\s+", "_", text)
    # Remove trailing underscores
    text = text.rstrip("_")
    return text


def ensure_cover_letters_folder():
    """Create cover_letters folder if it doesn't exist"""
    folder = Path("cover_letters")
    folder.mkdir(exist_ok=True)
    return folder


def generate_cover_letter_pdf(job, resume_data, folder):
    """
    Generate a professional one-page cover letter PDF
    Customized for Japan/APAC/international roles when applicable
    Returns the file path if successful, empty string otherwise
    """
    try:
        company = job.get("company", "Hiring Team").strip()
        title = job.get("title", "Position").strip()
        description = (job.get("description") or "").lower()
        
        # Detect if this is a Japan/APAC/international role
        is_japan_apac_role = any(term in description for term in ["japan", "tokyo", "apac", "asia-pacific", "international", "global"])
        is_localization_role = "localization" in description
        is_gaming_music_role = any(term in description for term in ["gaming", "music", "events"])
        
        # Create clean filename
        first_name = "Ben"
        last_name = "Goodrum"
        company_clean = clean_filename(company)
        title_clean = clean_filename(title)
        filename = f"{first_name}_{last_name}_Cover_Letter_{company_clean}_{title_clean}.pdf"
        filepath = folder / filename
        
        # Get today's date
        today = datetime.now().strftime("%B %d, %Y")
        
        # Create PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=10)
        
        # Margins: top, left, right, bottom
        pdf.set_margins(left=0.75, top=0.5, right=0.75)
        
        # Header: Name and contact
        pdf.set_font("Helvetica", "B", size=12)
        pdf.cell(0, 5, f"{first_name} {last_name}", ln=True, align="C")
        pdf.set_font("Helvetica", size=9)
        pdf.cell(0, 4, "Denver, CO | 773-793-4185 | ben_goodrum@yahoo.com", ln=True, align="C")
        pdf.ln(2)
        
        # Date
        pdf.set_font("Helvetica", size=10)
        pdf.cell(0, 4, today, ln=True)
        pdf.ln(1)
        
        # Recipient info
        pdf.cell(0, 4, f"{company}", ln=True)
        pdf.cell(0, 4, "Hiring Team", ln=True)
        pdf.ln(1)
        
        # Greeting
        pdf.cell(0, 4, "Dear Hiring Team,", ln=True)
        pdf.ln(1)
        
        # Paragraph 1: Interest in role (customized for Japan/APAC)
        skills = resume_data.get("skills", [])
        skill_phrase = ", ".join(skills[:2]) if len(skills) >= 2 else (skills[0] if skills else "strong organizational skills")
        
        if is_japan_apac_role or is_localization_role:
            para1 = (
                f"I am writing to express my strong interest in the {title} position at {company}. "
                f"With proven experience in operations coordination and a demonstrated ability to support business across diverse workflows and international contexts, "
                "I am eager to contribute to your team's global operations and expansion efforts."
            )
        elif is_gaming_music_role:
            para1 = (
                f"I am writing to express my strong interest in the {title} position at {company}. "
                f"With experience in {skill_phrase} and a passion for the gaming and music industries, "
                "I am excited to support your team's creative vision and operational excellence."
            )
        else:
            para1 = (
                f"I am writing to express my strong interest in the {title} position at {company}. "
                f"With proven experience in {skill_phrase} and a demonstrated ability to support operational excellence, "
                "I am confident I can make an immediate impact on your team."
            )
        
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 4, para1)
        pdf.ln(1)
        
        # Paragraph 2: Relevant background (customized for Japan/APAC)
        titles = resume_data.get("titles", [])
        title_phrase = titles[0] if titles else "coordination and administrative support"
        
        if is_japan_apac_role:
            para2 = (
                f"In my background in operations coordination, I have developed strong capabilities in managing workflows across teams, "
                "coordinating projects, and supporting organizational scaling. I bring systems thinking, attention to detail, and the ability to learn quickly—"
                "skills that are essential for supporting international business operations. I am particularly drawn to this role because of the opportunity to build "
                "expertise in global operations and international markets."
            )
        elif is_localization_role:
            para2 = (
                f"In my previous work in operations coordination, I have developed strong project management capabilities and learned to think systematically about processes. "
                "I am excited by the prospect of applying these skills to localization efforts, where precision, workflow optimization, and international collaboration are crucial. "
                "My ability to understand complex workflows and my commitment to quality make me well-suited to supporting your localization initiatives."
            )
        elif is_gaming_music_role:
            para2 = (
                f"In my previous roles, I have developed strong project coordination capabilities and excelled at supporting teams through detailed organization and communication. "
                "I understand the fast-paced, creative demands of the gaming and music industries, and I am committed to supporting your team's success. "
                "My background has prepared me to handle the multifaceted challenges of operations in creative industries."
            )
        else:
            para2 = (
                f"In my previous roles as a {title_phrase}, I have developed strong capabilities in managing workflows, "
                "coordinating team communication, and ensuring projects stay on schedule. "
                "I excel at improving efficiency, maintaining attention to detail, and supporting teams to meet their goals. "
                "My background has prepared me well for the challenges and responsibilities of this role."
            )
        
        pdf.multi_cell(0, 4, para2)
        pdf.ln(1)
        
        # Paragraph 3: Call to action
        if is_japan_apac_role or is_localization_role:
            para3 = (
                "I would welcome the opportunity to discuss how my operations background, systems thinking, and eagerness to learn can contribute to your team's success. "
                "I am available for a conversation at your convenience and look forward to learning more about this opportunity."
            )
        else:
            para3 = (
                "I would welcome the opportunity to discuss how my experience and commitment to operational excellence can contribute to your team's success. "
                "I am available for a conversation at your convenience and look forward to learning more about this opportunity."
            )
        
        pdf.multi_cell(0, 4, para3)
        pdf.ln(1)
        
        # Closing
        pdf.cell(0, 4, "Best regards,", ln=True)
        pdf.ln(3)
        pdf.cell(0, 4, f"{first_name} {last_name}", ln=True)
        
        # Save PDF
        pdf.output(str(filepath))
        return str(filepath)
        
    except Exception as e:
        print(f"⚠️  Error generating PDF for {company} {title}: {e}")
        return ""


def parse_salary_min(job):
    salary_min = job.get("salary_min")
    if salary_min is None or salary_min == "":
        return None
    try:
        return float(salary_min)
    except (TypeError, ValueError):
        return None


def classify_experience_requirement(job, config=None):
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()

    if any(pattern in title or pattern in description for pattern in EXPERIENCE_SKIP_PATTERNS):
        return "Skip"
    if any(pattern in title or pattern in description for pattern in EXPERIENCE_APPLY_PATTERNS):
        return "Apply"
    if any(pattern in title or pattern in description for pattern in EXPERIENCE_MAYBE_PATTERNS):
        return "Maybe"
    return "Skip"


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


def generate_application_plan(jobs, resume_data, config, output_file="application_plan.csv"):
    applied_entries = load_applied_jobs()
    print(f"Loaded {len(applied_entries)} applied jobs")
    
    plan_rows = []
    
    # Ensure cover_letters folder exists
    cover_letters_folder = ensure_cover_letters_folder()
    
    min_score = config.get("preferences", {}).get("min_score", 0)
    max_results = config.get("preferences", {}).get("max_results", len(jobs))
    daily_target = config.get("daily_target_results", 20)
    allow_seen = config.get("allow_seen_jobs", False)
    seen_entries = load_seen_jobs()

    skipped_applied = 0
    skipped_seen = 0
    skipped_low_salary = 0
    skipped_experience = 0
    saved_pdf_count = 0

    for job in jobs:
        score = job.get("score", 0)
        if score < min_score:
            continue
        if is_applied_or_excluded(job, applied_entries):
            skipped_applied += 1
            continue
        if is_seen_or_excluded(job, seen_entries, allow_seen=allow_seen):
            skipped_seen += 1
            continue

        experience_requirement = classify_experience_requirement(job, config=config)
        if experience_requirement == "Skip":
            skipped_experience += 1
            continue

        interview_prob, reason_to_apply = calculate_interview_probability(job, resume_data, score)
        salary_status = determine_salary_status(job, config)
        if salary_status == "below_minimum":
            skipped_low_salary += 1
            continue

        strong_fit = score >= 70 or interview_prob == "High"
        if salary_status == "unknown" and not strong_fit:
            skipped_low_salary += 1
            continue

        should_apply = determine_should_apply(interview_prob, experience_requirement, score)
        if should_apply == "No":
            continue

        bullets = build_resume_bullets(job, resume_data)
        short_message = build_short_message(job, resume_data)
        role_category = classify_role_category(job)
        tech_fit_reason = build_tech_fit_reason(job)
        
        # New Japan/APAC fields
        japan_connection = calculate_japan_connection(job, role_category)
        travel_potential = calculate_travel_potential(job, role_category)
        why_this_moves_me = determine_why_moves_toward_japan(job, role_category, japan_connection)
        realistic_fit_score = calculate_realistic_fit_score(job, resume_data, config)
        stretch_level = calculate_stretch_level(job, resume_data, config)
        next_skill = determine_next_skill_to_learn(job, resume_data)

        cover_letter_pdf = ""
        if should_apply in ["Apply", "Maybe"]:
            cover_letter_pdf = generate_cover_letter_pdf(job, resume_data, cover_letters_folder)
            if cover_letter_pdf:
                saved_pdf_count += 1

        plan_rows.append({
            "job_id": job.get("job_id", ""),
            "company": job.get("company", "Unknown"),
            "title": job.get("title", "Unknown"),
            "fit_score": score,
            "priority": job.get("priority", "Medium"),
            "match_reasons": " | ".join(job.get("match_reasons", [])),
            "red_flags": " | ".join(job.get("red_flags", [])),
            "salary_min": job.get("salary_min", ""),
            "salary_max": job.get("salary_max", ""),
            "salary_status": salary_status,
            "interview_probability": interview_prob,
            "should_apply": should_apply,
            "experience_requirement": experience_requirement,
            "role_category": role_category,
            "tech_fit_reason": tech_fit_reason,
            "reason_to_apply": reason_to_apply,
            "resume_bullets": " | ".join(bullets),
            "short_message": short_message,
            "cover_letter_pdf": cover_letter_pdf,
            "link": job.get("link", ""),
            "status": "not_applied",
            # New Japan/APAC columns
            "japan_connection": japan_connection,
            "travel_potential": travel_potential,
            "why_this_moves_me_toward_japan": why_this_moves_me,
            "realistic_fit_score": realistic_fit_score,
            "stretch_level": stretch_level,
            "next_skill_to_learn": next_skill,
        })
        if len(plan_rows) >= daily_target:
            break

    # Sort by: Apply first, then High priority, then fit score, then salary
    should_apply_order = {"Apply": 0, "Maybe": 1, "No": 2}
    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    stretch_order = {"Low": 0, "Medium": 1, "High": 2}
    
    plan_rows.sort(key=lambda x: (
        should_apply_order.get(x["should_apply"], 2),
        priority_order.get(x.get("priority", "Medium"), 1),  # High priority first
        -x.get("fit_score", 0),  # Highest fit score first
        -(parse_salary_min(x) or 0),  # Highest salary first
    ))
    plan_rows = plan_rows[:max_results]

    print(f"\n📊 Filtering Summary:")
    print(f"  ✓ Total jobs processed: {len(jobs)}")
    print(f"  ✗ Skipped {skipped_applied} already-applied jobs")
    print(f"  ✗ Skipped {skipped_seen} already-seen jobs")
    print(f"  ✗ Skipped {skipped_low_salary} low-salary/unknown jobs")
    print(f"  ✗ Skipped {skipped_experience} high-experience jobs")
    print(f"  ✓ Final application plan: {len(plan_rows)} jobs\n")

    try:
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "job_id", "company", "title", "fit_score", "priority", "match_reasons", "red_flags",
                "salary_min", "salary_max", "salary_status",
                "interview_probability", "should_apply", "experience_requirement",
                "role_category", "tech_fit_reason", "reason_to_apply", "resume_bullets", "short_message", 
                "cover_letter_pdf", "link", "status",
                # New Japan/APAC columns
                "japan_connection", "travel_potential", "why_this_moves_me_toward_japan", 
                "realistic_fit_score", "stretch_level", "next_skill_to_learn"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in plan_rows:
                writer.writerow(row)
        print(f"✓ Saved {len(plan_rows)} applications to {output_file}")
        print(f"✓ PDFs generated: {saved_pdf_count}\n")
    except Exception as e:
        print(f"Error saving to {output_file}: {e}")


def fetch_real_jobs_adzuna(app_id, app_key, country="us", locations=None, results_per_search=20):
    """
    Fetch real jobs from Adzuna API.
    Searches target keywords in the chosen locations.
    """
    if locations is None:
        locations = ["Denver, CO", "remote"]

    jobs = []
    print("📡 Fetching real job listings from Adzuna API...")

    for location in locations:
        for keyword in TARGET_KEYWORDS:
            try:
                url = f"{ADZUNA_API_BASE}/{country}/search/1"
                params = {
                    "app_id": app_id,
                    "app_key": app_key,
                    "what": keyword,
                    "where": location,
                    "results_per_page": results_per_search,
                    "content-type": "application/json",
                }

                response = requests.get(url, params=params, timeout=12)
                if response.status_code != 200:
                    print(f"⚠️  Adzuna API error for '{keyword}' in '{location}': {response.status_code} {response.reason}")
                    continue

                data = response.json()
                for result in data.get("results", []):
                    jobs.append({
                        "company": result.get("company", {}).get("display_name", ""),
                        "title": result.get("title", ""),
                        "location": result.get("location", {}).get("display_name", ""),
                        "link": result.get("redirect_url", ""),
                        "description": result.get("description", ""),
                        "created": result.get("created", ""),
                        "salary_min": result.get("salary_min", ""),
                        "salary_max": result.get("salary_max", ""),
                    })
            except Exception as e:
                print(f"⚠️  Error fetching '{keyword}' from Adzuna in '{location}': {e}")
                continue

    unique_jobs = []
    seen = set()
    for job in jobs:
        company_key = normalize_match_key(job.get("company"))
        title_key = normalize_match_key(job.get("title"))
        key = (company_key, title_key)
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    print(f"✓ Found {len(unique_jobs)} unique job listings\n")
    return unique_jobs


def fetch_real_jobs_fallback():
    """
    Fallback: Sample curated job listings for entry-level roles
    Use this if API key is not available
    """
    print("ℹ️  Using sample jobs (to use real API, get free Adzuna credentials)\n")
    
    return [
        {
            "id": 1,
            "title": "Operations Coordinator",
            "company": "Tech Startup Denver",
            "location": "Denver, CO",
            "description": "Entry-level operations coordinator role. Support team coordination, scheduling, data entry. Excel skills required. Remote possible.",
        },
        {
            "id": 2,
            "title": "Business Operations Assistant",
            "company": "Marketing Firm",
            "location": "Remote",
            "description": "Junior business operations assistant. Help manage workflows, coordinate projects, support administrative tasks. Strong organizational skills needed.",
        },
        {
            "id": 3,
            "title": "Administrative Coordinator",
            "company": "Denver Business Services",
            "location": "Denver, CO",
            "description": "Administrative coordinator for growing company. Calendar management, scheduling, filing, basic reporting. Entry-level position.",
        },
        {
            "id": 4,
            "title": "Marketing Operations Coordinator",
            "company": "E-commerce Company",
            "location": "Remote",
            "description": "Coordinate marketing operations and campaigns. Entry-level role with growth potential. Spreadsheet and communication skills essential.",
        },
        {
            "id": 5,
            "title": "Business Administrator",
            "company": "Consulting Group",
            "location": "Denver, CO",
            "description": "Support business operations and administrative functions. Strong communication and organizational skills. Potential for advancement.",
        },
        {
            "id": 6,
            "title": "Operations Support Specialist",
            "company": "Financial Services",
            "location": "Remote",
            "description": "Entry-level operations support role. Data entry, process improvement, team coordination. Excel and communication skills important.",
        },
    ]


def score_job(job, keywords, config=None, job_title_weight=2):
    """
    Score a job using a point-based system.
    Uses the new scoring logic optimized for analyst/operations roles.
    """
    score = 40  # Base score
    match_reasons = []
    red_flags = []
    
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    text = f"{title} {description}"
    salary_min = job.get("salary_min")
    
    try:
        salary_min_value = float(salary_min) if (salary_min and salary_min != "") else None
    except (TypeError, ValueError):
        salary_min_value = None
    
    # 1. Check for target roles
    target_roles = [
        "operations analyst",
        "business analyst",
        "business systems analyst",
        "technical operations coordinator",
        "technical project coordinator",
        "product operations associate",
        "revenue operations analyst",
        "revops",
        "sales operations analyst",
        "workflow automation specialist",
        "implementation specialist",
        "data operations analyst",
        "qa analyst",
    ]
    
    for role in target_roles:
        if role in title:
            score += 40
            match_reasons.append(f"Target role: {role}")
            break
    
    # 2. Positive keywords
    positive_keywords = {
        "analyst": 20,
        "operations": 15,
        "implementation": 15,
        "systems": 15,
        "business": 15,
        "automation": 15,
        "process improvement": 10,
        "workflow": 10,
        "documentation": 10,
        "requirements gathering": 10,
        "saas": 10,
        "crm": 10,
        "salesforce": 10,
        "jira": 10,
        "azure devops": 10,
        "excel": 10,
        "google sheets": 10,
        "python": 10,
        "sql": 10,
    }
    
    for keyword, points in positive_keywords.items():
        if keyword in text:
            score += points
            if keyword not in [r for r in match_reasons]:
                match_reasons.append(f"✓ {keyword}")
    
    # 3. Remote bonus
    if "remote" in text or "hybrid" in text or "work from home" in text:
        score += 30
        match_reasons.append("✓ Remote position")
    
    # 4. Apply penalties
    penalties = {
        "senior": -50,
        "manager": -50,
        "director": -50,
        "principal": -50,
        "lead": -50,
        "5+ years": -40,
        "6+ years": -40,
        "7+ years": -40,
        "8+ years": -40,
        "construction": -40,
        "recruiting coordinator": -40,
        "warehouse": -40,
        "logistics": -40,
        "event associate": -40,
        "event coordinator": -40,
        "grants coordinator": -40,
        "project coordinator": -30,
        "administrative coordinator": -30,
        "travel coordinator": -40,
        "localization": -40,
        "gaming": -40,
        "healthcare staffing": -40,
        "onsite only": -25,
    }
    
    for keyword, penalty in penalties.items():
        if keyword in text:
            score += penalty
            red_flags.append(f"✗ {keyword}")
    
    # 5. Weak fit penalties
    weak_keywords = {
        "event": -30,
        "grants": -30,
        "travel": -25,
        "hospitality": -25,
    }
    
    for keyword, penalty in weak_keywords.items():
        if keyword in text and keyword not in "event coordinator":  # Don't double-penalize
            score += penalty
            red_flags.append(f"⚠ {keyword}")
    
    # 6. Salary scoring
    if salary_min_value:
        if salary_min_value >= 70000:
            score += 20
            match_reasons.append(f"✓ ${salary_min_value:,.0f}")
        elif salary_min_value < 50000:
            score -= 20
            red_flags.append(f"✗ Low salary: ${salary_min_value:,.0f}")
    
    # Clamp score
    score = max(0, min(100, score))
    
    # Determine priority
    if score >= 70:
        priority = "High"
    elif score >= 40:
        priority = "Medium"
    else:
        priority = "Low"
    
    return {
        "score": score,
        "priority": priority,
        "match_reasons": match_reasons[:5],
        "red_flags": red_flags[:3],
    }


def score_jobs(jobs, keywords, config=None):
    """Score all jobs and return sorted by score (using new scoring system)"""
    scored_jobs = []
    for job in jobs:
        result = score_job(job, keywords, config=config)
        job_with_score = {
            **job,
            "score": result["score"],
            "priority": result["priority"],
            "match_reasons": result["match_reasons"],
            "red_flags": result["red_flags"],
        }
        scored_jobs.append(job_with_score)
    return sorted(scored_jobs, key=lambda x: x["score"], reverse=True)


def save_results(jobs, output_file="jobs.csv"):
    """Save scored jobs to CSV file"""
    if not jobs:
        print("No jobs to save!")
        return
    
    try:
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "job_id", "company", "title", "location", "link", "fit_score", "priority",
                "match_reasons", "red_flags", "salary_min", "salary_max",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for job in jobs:
                row = {
                    "job_id": job.get("job_id", ""),
                    "company": job.get("company", ""),
                    "title": job.get("title", ""),
                    "location": job.get("location", ""),
                    "link": job.get("link", ""),
                    "fit_score": job.get("score", ""),
                    "priority": job.get("priority", ""),
                    "match_reasons": " | ".join(job.get("match_reasons", [])) if isinstance(job.get("match_reasons"), list) else job.get("match_reasons", ""),
                    "red_flags": " | ".join(job.get("red_flags", [])) if isinstance(job.get("red_flags"), list) else job.get("red_flags", ""),
                    "salary_min": job.get("salary_min", ""),
                    "salary_max": job.get("salary_max", ""),
                }
                writer.writerow(row)
        print(f"✓ Saved {len(jobs)} jobs to {output_file}")
    except Exception as e:
        print(f"Error saving to {output_file}: {e}")


def append_seen_jobs(jobs, seen_file=SEEN_JOBS_FILE):
    """Append new jobs to seen_jobs.csv without duplicating existing entries."""
    seen_entries = load_seen_jobs(seen_file)
    seen_keys = set()
    
    # Build set of keys from existing seen jobs (already normalized from load_seen_jobs)
    for entry in seen_entries:
        company = entry.get("company", "")
        title = entry.get("title", "")
        link = entry.get("link", "")
        key = (company, title, link)
        seen_keys.add(key)

    rows_to_append = []
    for job in jobs:
        # Normalize the new job using same logic
        company_norm = normalize_match_key(job.get("company", ""))
        title_norm = normalize_match_key(job.get("title", ""))
        link_norm = normalize_link(job.get("link", ""))
        key = (company_norm, title_norm, link_norm)
        
        # Skip if already seen
        if key in seen_keys:
            continue
        
        # Add to set and to rows to append
        seen_keys.add(key)
        rows_to_append.append({
            "job_id": job.get("job_id", ""),
            "company": job.get("company", ""),
            "title": job.get("title", ""),
            "link": job.get("link", ""),
            "salary_min": job.get("salary_min", ""),
            "salary_max": job.get("salary_max", ""),
            "score": job.get("score", ""),
        })

    if not rows_to_append:
        print(f"   ℹ️  No new jobs to add to {SEEN_JOBS_FILE} (all are duplicates)")
        return 0

    file_exists = Path(seen_file).exists()
    try:
        with open(seen_file, "a", newline="", encoding="utf-8") as f:
            fieldnames = ["job_id", "company", "title", "link", "salary_min", "salary_max", "score"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for row in rows_to_append:
                writer.writerow(row)
    except Exception as e:
        print(f"Error appending to {seen_file}: {e}")
        return 0
    return len(rows_to_append)


def print_top_matches(jobs, limit=5):
    """Print top matching jobs to console"""
    matching_jobs = [job for job in jobs if job["score"] > 0]
    
    if not matching_jobs:
        print("\n❌ No matching jobs found. Try adjusting your keywords!")
        return
    
    print("\n" + "=" * 70)
    print("🎯 TOP JOB MATCHES")
    print("=" * 70)
    
    for rank, job in enumerate(matching_jobs[:limit], 1):
        print(f"\n{rank}. {job['title']}")
        print(f"   Company: {job['company']}")
        print(f"   Location: {job.get('location', 'Unknown')}")
        print(f"   Score: {job['score']}")
        if "description" in job:
            print(f"   Details: {job['description'][:70]}...")
    
    print("\n" + "=" * 70)
    print(f"Found {len(matching_jobs)} matching jobs total")
    print("=" * 70 + "\n")


def main():
    """Main function"""
    print("\n🔍 Job Search Assistant - REAL Job Listings\n")
    
    # Load configuration
    config = load_config()
    if not config:
        print("Using default keywords...")
        keywords = ["operations", "administrative", "coordinator"]
    else:
        keywords = config.get("keywords", ["operations", "administrative"])
        print(f"Keywords: {', '.join(keywords)}\n")
    
    # Load resume and extract strengths
    resume_data = extract_resume_data("resume.txt")
    print(f"Resume keywords found: {', '.join(resume_data.get('keywords', [])[:5])}")
    print(f"Resume skills found: {', '.join(resume_data.get('skills', [])[:5])}")
    print(f"Resume titles found: {', '.join(resume_data.get('titles', [])[:5])}\n")

    # Check for Adzuna credentials
    adzuna_id = config.get("adzuna_app_id") if config else None
    adzuna_key = config.get("adzuna_app_key") if config else None
    country = config.get("country", "us") if config else "us"
    results_per_search = config.get("results_per_search", 20) if config else 20

    locations = config.get("locations") if config else None
    if not locations:
        location = config.get("location", "Denver, CO") if config else "Denver, CO"
        locations = [location]
    if "remote" not in [loc.lower() for loc in locations]:
        locations.append("remote")

    if not adzuna_id or not adzuna_key:
        print("❌ Missing Adzuna credentials in config.yaml. Add adzuna_app_id and adzuna_app_key.")
        return

    jobs = fetch_real_jobs_adzuna(
        adzuna_id,
        adzuna_key,
        country=country,
        locations=locations,
        results_per_search=results_per_search,
    )
    if not jobs:
        print("❌ Could not fetch any jobs from Adzuna. Please verify your credentials and internet connection.")
        return

    print(f"\n📥 Fetched: {len(jobs)} total job listings from Adzuna")
    applied_entries = load_applied_jobs()
    print(f"📋 Loaded: {len(applied_entries)} previously applied jobs")
    seen_entries = load_seen_jobs()
    print(f"👁️  Loaded: {len(seen_entries)} previously seen jobs")

    print(f"\n🔍 Starting job filtering...\n")
    
    # Step 1: Filter by config (title/description matching)
    pre_applied_filter = len(jobs)
    filtered_jobs = filter_jobs(jobs, config)
    print(f"   ✓ After config filters: {len(filtered_jobs)} jobs")
    
    # Step 2: Remove already applied
    pre_seen_filter = len(filtered_jobs)
    filtered_jobs, applied_skipped = filter_applied_jobs(filtered_jobs, applied_entries)
    print(f"   ✗ Skipped {applied_skipped} already-applied jobs → {len(filtered_jobs)} remain")
    
    # Step 3: Remove already seen
    pre_dup_filter = len(filtered_jobs)
    filtered_jobs, seen_skipped = filter_seen_jobs(filtered_jobs, seen_entries, allow_seen=config.get("allow_seen_jobs", False))
    print(f"   ✗ Skipped {seen_skipped} already-seen jobs → {len(filtered_jobs)} remain")
    
    # Step 4: Remove duplicates within this run
    pre_score = len(filtered_jobs)
    filtered_jobs, duplicate_skipped = filter_duplicates(filtered_jobs)
    print(f"   ✗ Removed {duplicate_skipped} duplicate jobs within this run → {len(filtered_jobs)} remain")

    if not filtered_jobs:
        print("\n❌ No jobs matched your filters. Try adjusting config.yaml keywords and exclusions.")
        return

    print(f"\n⭐ Starting job scoring with new system...")
    scored_jobs = score_jobs(filtered_jobs, keywords, config)
    
    # Count by score/priority
    high_priority = [j for j in scored_jobs if j.get("priority") == "High"]
    medium_priority = [j for j in scored_jobs if j.get("priority") == "Medium"]
    low_priority = [j for j in scored_jobs if j.get("priority") == "Low"]
    
    print(f"   🔴 High priority ({len(high_priority)} jobs, score >= 70)")
    print(f"   🟡 Medium priority ({len(medium_priority)} jobs, score 40-69)")
    print(f"   🔵 Low priority ({len(low_priority)} jobs, score < 40)")

    print_top_matches(scored_jobs, limit=10)

    generate_application_plan(scored_jobs, resume_data, config)
    
    save_results(scored_jobs)
    append_count = append_seen_jobs(scored_jobs)
    if append_count:
        print(f"   ✓ Added {append_count} new jobs to {SEEN_JOBS_FILE}")
    
    print("\n💡 To use real job listings from Adzuna:")
    print("   1. Get free API credentials: https://developer.adzuna.com/")
    print("   2. Add to config.yaml: adzuna_app_id and adzuna_app_key")
    print("   3. Run this script again\n")


if __name__ == "__main__":
    main()
