"""Lightweight per-job status tracking.

Status is stored in its own CSV (data/job_status.csv) keyed by the normalized
job id. This keeps the existing application_plan.csv schema untouched while
letting the UI track Seen / Saved / Applied / Rejected and free-text notes.
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

logger = logging.getLogger("job_assistant.status")

STATUS_FILE = helpers.DATA_DIR / "job_status.csv"
STATUS_FIELDS = ["id", "status", "notes", "company", "title", "url", "updated_at"]
VALID_STATUSES = ["Seen", "Saved", "Applied", "Rejected"]


def load_statuses(status_file=STATUS_FILE):
    """Return a dict mapping job id -> {status, notes, ...}."""
    statuses = {}
    if not Path(status_file).exists():
        return statuses
    try:
        with open(status_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                job_id = (row.get("id") or "").strip()
                if not job_id:
                    continue
                statuses[job_id] = {
                    "status": (row.get("status") or "Seen").strip() or "Seen",
                    "notes": row.get("notes") or "",
                    "company": row.get("company") or "",
                    "title": row.get("title") or "",
                    "url": row.get("url") or "",
                    "updated_at": row.get("updated_at") or "",
                }
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to read status file: %s", exc)
        return {}
    return statuses


def _write_all(statuses, status_file=STATUS_FILE):
    status_file.parent.mkdir(parents=True, exist_ok=True)
    with open(status_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=STATUS_FIELDS)
        writer.writeheader()
        for job_id, data in sorted(statuses.items()):
            writer.writerow({
                "id": job_id,
                "status": data.get("status", "Seen"),
                "notes": data.get("notes", ""),
                "company": data.get("company", ""),
                "title": data.get("title", ""),
                "url": data.get("url", ""),
                "updated_at": data.get("updated_at", ""),
            })


def set_status(job_id, status=None, notes=None, company="", title="", url="", status_file=STATUS_FILE):
    """Create or update the status/notes for a single job id."""
    job_id = (job_id or "").strip()
    if not job_id:
        return None
    if status is not None and status not in VALID_STATUSES:
        logger.warning("Ignoring invalid status '%s' for %s", status, job_id)
        status = None
    statuses = load_statuses(status_file)
    entry = statuses.get(job_id, {"status": "Seen", "notes": "", "company": "", "title": "", "url": ""})
    if status is not None:
        entry["status"] = status
    if notes is not None:
        entry["notes"] = notes
    if company:
        entry["company"] = company
    if title:
        entry["title"] = title
    if url:
        entry["url"] = url
    entry["updated_at"] = datetime.now().isoformat(timespec="seconds")
    statuses[job_id] = entry
    _write_all(statuses, status_file)
    return entry


def get_status(job_id, status_file=STATUS_FILE):
    return load_statuses(status_file).get((job_id or "").strip())
