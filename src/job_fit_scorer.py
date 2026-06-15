import re

# TARGET ROLES (HIGH FIT)
TARGET_ROLES = [
    "operations analyst",
    "business analyst",
    "business systems analyst",
    "technical operations coordinator",
    "technical project coordinator",
    "product operations associate",
    "revenue operations analyst",
    "revops associate",
    "sales operations analyst",
    "workflow automation specialist",
    "implementation specialist",
    "data operations analyst",
    "qa analyst",
    "customer success operations",
]

# POSITIVE KEYWORDS WITH POINTS
POSITIVE_KEYWORDS = {
    # Role keywords (high value)
    "operations analyst": 35,
    "business systems analyst": 35,
    "implementation specialist": 30,
    "revops": 30,
    "product operations": 30,
    "technical operations": 25,
    "workflow automation": 25,
    "analyst": 20,
    "operations": 15,
    "implementation": 15,
    "systems": 15,
    "business": 15,
    "automation": 15,
    
    # Process/skills keywords
    "process improvement": 12,
    "workflow": 12,
    "documentation": 10,
    "requirements gathering": 10,
    "stakeholder communication": 12,
    
    # Tech keywords (now more valuable)
    "saas": 12,
    "crm": 12,
    "salesforce": 12,
    "jira": 15,
    "azure devops": 12,
    "excel": 15,
    "google sheets": 12,
    "python": 12,
    "sql": 15,
    "dashboards": 12,
    "reporting": 12,
    
    # Location
    "remote": 30,
    
    # Salary
    "salary >= 70000": 20,  # Special flag - will be checked separately
}

# PENALTIES
PENALTIES = {
    # Senior/leadership (high priority to exclude)
    "senior": -50,
    "manager": -50,
    "director": -50,
    "principal": -50,
    "lead": -50,
    
    # Experience requirements - NOW PENALTIES INSTEAD OF HARD FILTERS
    # 0-2 years = no penalty
    # 3 years = light penalty
    "3 years": -15,
    "3+ years": -15,
    
    # 4-5 years = moderate penalty (but allow analyst roles through)
    "4 years": -25,
    "4+ years": -25,
    "5 years": -25,
    "5+ years": -30,
    
    # 6+ years = strong penalty (but allow analyst roles through)
    "6+ years": -40,
    "7+ years": -40,
    "8+ years": -40,
    "9+ years": -40,
    "10+ years": -50,
    
    # Excluded industries/roles
    "construction": -40,
    "recruiting coordinator": -40,
    "warehouse": -40,
    "logistics": -40,
    "event associate": -40,
    "event coordinator": -40,
    "grants coordinator": -40,
    "project coordinator": -30,  # Lower penalty - not as bad but still not target
    "administrative coordinator": -30,
    "travel coordinator": -40,
    "localization": -40,
    "gaming": -40,
    "healthcare": -30,
    "healthcare staffing": -40,
    "nursing": -35,
    "field technician": -40,
    "onsite only": -25,
    "onsite required": -25,
    
    # Salary
    "salary < 70000": -20,  # Will be checked separately
}

# Weak fit keywords to penalize
WEAK_FIT_KEYWORDS = {
    "event": -30,
    "grants": -30,
    "recruiting": -30,
    "travel": -25,
    "hospitality": -25,
    "healthcare": -25,
    "consultant": -20,
    "engineering": -30,
    "developer": -30,
}

GOOD_TITLES = [
    "operations analyst",
    "business analyst",
    "business systems analyst",
    "technical operations",
    "workflow automation",
    "process analyst",
    "implementation specialist",
    "revops",
    "sales operations",
    "data operations",
    "qa analyst",
    "automation specialist",
    "business systems coordinator",
    "operations associate",
]

def clean_text(text):
    """Normalize text for matching"""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.lower()).strip()

def score_job(job_title, job_description, salary_min=None):
    """
    Score a job using the new point-based system.
    Returns dict with score, priority, match_reasons, and red_flags
    """
    text = clean_text(job_title + " " + job_description)
    
    score = 40  # Base score
    match_reasons = []
    red_flags = []
    
    # 1. Check for target role titles
    for role in TARGET_ROLES:
        if role in text:
            score += 40
            match_reasons.append(f"Target role: {role}")
            break
    
    # 2. Check for good title keywords
    for title in GOOD_TITLES:
        if title in text:
            score += 20
            match_reasons.append(f"Good title keyword: {title}")
            break
    
    # 3. Apply positive keywords
    for keyword, points in POSITIVE_KEYWORDS.items():
        if keyword == "salary >= 70000":  # Skip special salary keyword
            continue
        if keyword == "remote":
            if "remote" in text or "hybrid" in text or "work from home" in text:
                score += points
                match_reasons.append("✓ Remote position")
        elif keyword in text:
            score += points
            if keyword not in [m.split(":")[1].strip() if ":" in m else "" for m in match_reasons]:
                match_reasons.append(f"✓ {keyword}")
    
    # 4. Apply penalties for excluded keywords and weak fit
    for keyword, penalty in PENALTIES.items():
        if keyword == "salary >= 70000" or keyword == "salary < 70000":
            continue  # Handle separately
        if keyword in text:
            score += penalty
            red_flags.append(f"✗ {keyword}")
    
    # 5. Apply weak fit penalties
    for keyword, penalty in WEAK_FIT_KEYWORDS.items():
        if keyword in text:
            score += penalty
            red_flags.append(f"⚠ Weak fit: {keyword}")
    
    # 6. Check salary
    if salary_min is not None:
        try:
            salary_val = float(salary_min)
            if salary_val >= 70000:
                score += 20
                match_reasons.append(f"✓ Salary: ${salary_val:,.0f}")
            elif salary_val < 50000:
                score -= 20
                red_flags.append(f"✗ Low salary: ${salary_val:,.0f}")
            else:
                match_reasons.append(f"Salary: ${salary_val:,.0f}")
        except (TypeError, ValueError):
            pass
    
    # 7. Clamp score to 0-100
    score = max(0, min(100, score))
    
    # 8. Determine priority
    if score >= 70:
        priority = "High"
    elif score >= 40:
        priority = "Medium"
    else:
        priority = "Low"
    
    # 9. Generate recommendation
    if score >= 80 and not any("✗" in flag for flag in red_flags):
        recommendation = "Apply now — strong fit."
    elif score >= 65:
        recommendation = "Apply if company looks good."
    elif score >= 50:
        recommendation = "Maybe — review carefully before applying."
    else:
        recommendation = "Skip or low priority."
    
    return {
        "score": score,
        "priority": priority,
        "match_reasons": match_reasons[:5],  # Top 5 reasons
        "red_flags": red_flags[:3],  # Top 3 red flags
        "recommendation": recommendation,
    }

def get_recommendation(score, red_flags):
    """Legacy function for compatibility"""
    if score >= 80 and not red_flags:
        return "Apply now — strong fit."
    if score >= 65:
        return "Apply if the company looks good."
    if score >= 50:
        return "Maybe — tailor resume first."
    return "Skip or low priority."

if __name__ == "__main__":
    # Test the scorer
    title = input("Job title: ")
    
    try:
        with open("job_description.txt", "r", encoding="utf-8") as file:
            description = file.read()
    except FileNotFoundError:
        description = ""
    
    salary = input("Salary min (or press Enter to skip): ")
    salary_min = None
    if salary:
        try:
            salary_min = float(salary)
        except ValueError:
            pass
    
    result = score_job(title, description, salary_min)
    
    print("\n--- Job Fit Report ---")
    print(f"Score: {result['score']}/100")
    print(f"Priority: {result['priority']}")
    print(f"Recommendation: {result['recommendation']}")
    
    if result["match_reasons"]:
        print("\nMatch Reasons:")
        for reason in result["match_reasons"]:
            print(f"  {reason}")
    
    if result["red_flags"]:
        print("\nRed Flags:")
        for flag in result["red_flags"]:
            print(f"  {flag}")
