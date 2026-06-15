"""Handshake job source — manual, paste-based import only.

IMPORTANT (by design and policy):
  * This module does NOT log in to Handshake.
  * It does NOT scrape, automate a browser, or bypass CAPTCHA / MFA / rate limits.
  * It does NOT auto-apply to anything.

The user manually pastes a Handshake job URL and/or the job description text
that they are already authorized to view. We parse that text into the shared
normalized schema, deduplicate it against existing results, and store it so it
can be scored and used for tailored application materials like any other job.
"""

import csv
import sys
import logging
from pathlib import Path
from datetime import datetime

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import helpers  # noqa: E402
import services  # noqa: E402

logger = logging.getLogger("job_assistant.handshake")

HANDSHAKE_JOBS_FILE = helpers.DATA_DIR / "handshake_jobs.csv"
SOURCE_NAME = "Handshake"


def _guess_field(lines, label):
    """Find 'Label: value' style lines in pasted text."""
    label_lower = label.lower()
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith(label_lower):
            parts = stripped.split(":", 1)
            if len(parts) == 2 and parts[1].strip():
                return parts[1].strip()
    return ""


def parse_handshake_job(pasted_text="", url="", title="", company="", location="",
                        salary_min="", salary_max=""):
    """Build a normalized Handshake job from manually provided fields/text.

    Explicit fields always win. Anything not supplied is best-effort guessed
    from the pasted description (looking for 'Title:', 'Company:', etc.).
    """
    text = (pasted_text or "").strip()
    lines = [ln for ln in text.splitlines() if ln.strip()]

    title = title.strip() or _guess_field(lines, "title") or _guess_field(lines, "job title")
    company = company.strip() or _guess_field(lines, "company") or _guess_field(lines, "employer")
    location = location.strip() or _guess_field(lines, "location")

    # Fallback: use the first non-empty line as the title if still unknown.
    if not title and lines:
        title = lines[0].strip()[:120]

    raw = {
        "source": SOURCE_NAME,
        "title": title,
        "company": company,
        "location": location,
        "url": url.strip(),
        "description": text,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "date_found": datetime.now().strftime("%Y-%m-%d"),
    }
    return services.normalize_job(raw, source=SOURCE_NAME)


def is_duplicate(job, existing_jobs):
    """True if job matches an existing job by url, or company+similar title."""
    job_url = helpers.normalize_link(job.get("url", ""))
    job_company = helpers.normalize_match_key(job.get("company", ""))
    job_title = job.get("title", "")
    for existing in existing_jobs:
        existing_url = helpers.normalize_link(existing.get("url", "") or existing.get("link", ""))
        if job_url and existing_url and job_url == existing_url:
            return True
        existing_company = helpers.normalize_match_key(existing.get("company", ""))
        if job_company and existing_company and job_company == existing_company:
            if helpers.titles_similar(job_title, existing.get("title", "")):
                return True
    return False


def load_handshake_jobs(jobs_file=HANDSHAKE_JOBS_FILE):
    """Load previously imported Handshake jobs in normalized form."""
    if not Path(jobs_file).exists():
        return []
    rows = []
    try:
        with open(jobs_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(services.normalize_job(row, source=SOURCE_NAME))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to read Handshake jobs: %s", exc)
        return []
    return rows


def save_handshake_job(job, jobs_file=HANDSHAKE_JOBS_FILE):
    """Append a normalized Handshake job to its store, deduplicated."""
    existing = load_handshake_jobs(jobs_file)
    if is_duplicate(job, existing):
        return False, "Duplicate of an already-imported Handshake job."
    jobs_file.parent.mkdir(parents=True, exist_ok=True)
    file_exists = Path(jobs_file).exists()
    with open(jobs_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=services.SCHEMA_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow({key: job.get(key, "") for key in services.SCHEMA_FIELDS})
    return True, "Imported."


def import_handshake_job(pasted_text="", url="", title="", company="", location="",
                         salary_min="", salary_max="", existing_jobs=None):
    """Parse + dedupe + persist a manually supplied Handshake job.

    Returns (job_dict, imported_bool, message).
    """
    job = parse_handshake_job(
        pasted_text=pasted_text, url=url, title=title, company=company,
        location=location, salary_min=salary_min, salary_max=salary_max,
    )
    if not job.get("title") and not job.get("company"):
        return job, False, "Need at least a title or company (paste the job description or fill the fields)."

    # Dedupe against the current on-screen results too, if provided.
    if existing_jobs and is_duplicate(job, existing_jobs):
        return job, False, "Duplicate of a job already in your results."

    imported, message = save_handshake_job(job)
    return job, imported, message
