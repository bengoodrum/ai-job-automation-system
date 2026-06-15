"""Shared service layer used by both the CLI and the Streamlit UI.

This module is intentionally additive: it wraps the existing helpers/scorer/main
modules and exposes a normalized job schema plus a few convenience functions so
that the web UI and the command line can share the exact same logic.
"""

import csv
import sys
import logging
from pathlib import Path
from datetime import datetime

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import helpers  # noqa: E402
import scorer  # noqa: E402

logger = logging.getLogger("job_assistant.services")

DATA_DIR = helpers.DATA_DIR
RESULTS_CACHE_FILE = DATA_DIR / "results_cache.csv"

# Normalized job schema shared across the app.
SCHEMA_FIELDS = [
    "id", "source", "title", "company", "location", "remote_type",
    "salary_min", "salary_max", "url", "description", "date_found",
    "score", "fit_reasons", "concerns", "status", "notes",
]

REMOTE_TERMS = ["remote", "work from home", "fully remote", "telecommute"]
HYBRID_TERMS = ["hybrid", "flexible location", "partially remote"]
ONSITE_TERMS = ["on-site", "on site", "onsite", "in office", "in-office"]


def detect_remote_type(job):
    """Infer remote/hybrid/on-site from a raw or normalized job dict."""
    title = (job.get("title") or "").lower()
    location = (job.get("location") or "").lower()
    description = (job.get("description") or "").lower()
    text = f"{title} {location} {description}"
    if any(term in text for term in HYBRID_TERMS):
        return "hybrid"
    if any(term in text for term in REMOTE_TERMS):
        return "remote"
    if any(term in text for term in ONSITE_TERMS):
        return "on-site"
    return "unknown"


def _as_list_string(value):
    if isinstance(value, list):
        return " | ".join(str(v) for v in value)
    return str(value or "")


def normalize_job(raw, source="Adzuna"):
    """Map an internal job dict (or CSV row) to the normalized schema."""
    job_id = (raw.get("id") or raw.get("job_id") or "").strip()
    if not job_id:
        job_id = helpers.generate_job_id(raw.get("company"), raw.get("title"))

    url = raw.get("url") or raw.get("link") or ""
    date_found = raw.get("date_found") or raw.get("created") or datetime.now().strftime("%Y-%m-%d")

    return {
        "id": job_id,
        "source": raw.get("source") or source,
        "title": raw.get("title") or "",
        "company": raw.get("company") or "",
        "location": raw.get("location") or "",
        "remote_type": raw.get("remote_type") or detect_remote_type(raw),
        "salary_min": raw.get("salary_min") or "",
        "salary_max": raw.get("salary_max") or "",
        "url": url,
        "description": raw.get("description") or "",
        "date_found": date_found,
        "score": raw.get("score") if raw.get("score") not in (None, "") else raw.get("fit_score", ""),
        "fit_reasons": _as_list_string(raw.get("fit_reasons") or raw.get("match_reasons")),
        "concerns": _as_list_string(raw.get("concerns") or raw.get("red_flags")),
        "status": raw.get("status") or "Seen",
        "notes": raw.get("notes") or "",
    }


def save_results_cache(jobs, cache_file=RESULTS_CACHE_FILE):
    """Persist normalized results (including description) for UI reloads."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SCHEMA_FIELDS)
        writer.writeheader()
        for job in jobs:
            normalized = normalize_job(job, source=job.get("source", "Adzuna"))
            writer.writerow({key: normalized.get(key, "") for key in SCHEMA_FIELDS})
    return cache_file


def load_results_cache(cache_file=RESULTS_CACHE_FILE):
    """Load previously cached normalized results, if any."""
    if not Path(cache_file).exists():
        return []
    rows = []
    try:
        with open(cache_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(normalize_job(row, source=row.get("source", "Adzuna")))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to read results cache: %s", exc)
        return []
    return rows


def run_search():
    """Run the existing search pipeline and return normalized scored jobs.

    Reuses main.run_main() so the UI executes the identical fetch/filter/score/
    output workflow as the CLI (including writing jobs.csv and cover letter PDFs).
    """
    import main  # local import to avoid any import cycle at module load
    try:
        scored_jobs = main.run_main() or []
    except Exception as exc:
        logger.exception("Search pipeline failed: %s", exc)
        raise
    normalized = [normalize_job(job, source="Adzuna") for job in scored_jobs]
    try:
        save_results_cache(normalized)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Could not write results cache: %s", exc)
    return normalized
