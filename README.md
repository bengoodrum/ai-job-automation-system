# AI-Assisted Job Automation System

A Python-based job automation workflow that searches, filters, ranks, and organizes job applications using APIs, configurable YAML logic, CSV pipelines, and automated PDF generation.

## Features

- ✅ Real job aggregation from Adzuna API
- ✅ Smart duplicate prevention with normalization
- ✅ Advanced experience-based scoring (penalties instead of hard filters)
- ✅ Application status tracking (review/applied/skipped)
- ✅ Intelligent company limiting (max 2 per company)
- ✅ Remote role prioritization
- ✅ Analyst/operations role boosting
- ✅ Customized cover letter generation with better formatting
- ✅ CSV tracking and exclusion system
- ✅ YAML-based configuration
- ✅ Application ranking and sorting
- ✅ Role categorization
- ✅ International/APAC job targeting support
- ✅ Cleanup utility for generated files

## Quick Start

```bash
pip install -r requirements.txt
python3 src/main.py
```

## Web App (Streamlit)

A local web dashboard is available alongside the CLI. It reuses the exact same
search/scoring pipeline and shared modules — nothing about the CLI changes.

```bash
# from the project root, with your venv active
pip install -r requirements.txt
streamlit run app.py
```

The dashboard lets you:

- **Run job search** (same Adzuna pipeline as the CLI)
- Filter by source, role category, remote/hybrid/on-site, minimum salary, and exclusion keywords
- Track status per job: **Seen / Saved / Applied / Rejected** (stored in `data/job_status.csv`)
- **Manually import a Handshake job** by pasting its URL and/or description (no login,
  scraping, CAPTCHA/MFA bypass, or auto-apply — paste only)
- **Generate a tailored resume + cover letter** for a selected job
- **Export results to CSV**

### Generated application materials

Tailored files are saved to:

```
outputs/applications/<company>_<role>_<date>/
  ├── tailored_resume.docx        # reordered/emphasized — never fabricated
  ├── cover_letter.docx
  ├── tailored_resume_preview.txt
  ├── cover_letter_preview.txt
  └── keyword_match_report.txt
```

Your master resume (`resume/resume.txt`) is read-only and never modified.

## Commands

### Generate Job Application Plan
```bash
python3 src/main.py
```
Fetches jobs from Adzuna API, scores them, and generates application_plan.csv with customized cover letters.

### Cleanup Generated Files
```bash
# Preview what will be deleted (no --confirm = dry run)
python3 src/main.py --cleanup --cleanup-type cover_letters

# Delete old cover letters modified more than 7 days ago
python3 src/main.py --cleanup --cleanup-type cover_letters --older-than 7 --confirm

# Archive resumes instead of deleting
python3 src/main.py --cleanup --cleanup-type data --archive --confirm

# Clean all generated files (cover letters + data outputs)
python3 src/main.py --cleanup --confirm
```

**Cleanup options:**
- `--type`: `cover_letters`, `resumes`, or `all_generated` (default: all_generated)
- `--older-than DAYS`: Only clean files older than X days (default: clean all)
- `--archive`: Move files to backup folder instead of deleting
- `--confirm`: Required to execute cleanup (without it, only shows preview)

**Protected files (never deleted):**
- `resume.txt` (your main resume)
- `config.yaml` and `config.example.yaml` (configuration)
- `*.csv` files (job tracking data)

## Configuration

Edit `config.yaml` to customize:

```yaml
keywords:
  - operations analyst
  - business systems analyst
  - implementation specialist
  # ... more keywords

exclude_keywords:
  - senior
  - director
  - manager
  # ... keywords to exclude

locations:
  - Denver, CO
  - remote

adzuna_app_id: YOUR_APP_ID
adzuna_app_key: YOUR_APP_KEY
```

Get free Adzuna credentials: https://developer.adzuna.com/

## Data Files

**Generated/Updated:**
- `application_plan.csv` - Top job candidates with scores, cover letters, and status
- `jobs.csv` - All scored jobs from current run
- `seen_jobs.csv` - Historical job listings (prevents re-processing)

**Manual Tracking:**
- `applied_jobs.csv` - Jobs you've applied to (created manually)
- `application_plan.csv:status` - Change to "applied" or "skipped" to track and exclude

**Generated Files:**
- `cover_letters/` - PDF cover letters for each job
- `backups/` - Archived files from cleanup

## Application Status Tracking

In `application_plan.csv`, the `status` column controls tracking:
- **review** (default) - New jobs to review
- **applied** - Jobs you've applied to (excludes from future runs)
- **skipped** - Jobs you reviewed but don't want to apply to

Change the status manually, then future runs will automatically exclude applied/skipped jobs and any duplicate company/title combinations.

## Scoring System

Jobs are scored 0-100 based on:

**Boosts (+):**
- Operations/business analyst titles: +35
- Remote positions: +30
- Implementation specialist: +30
- Workflow automation/RevOps: +25
- Technical keywords: +12-15 (SQL, Excel, Jira, automation)
- Strong salary (70k+): +20

**Penalties (-):**
- Senior/manager/director: -50
- 3 years experience: -15
- 4-5 years experience: -25
- 6+ years experience: -40 (but analysts still score)
- Healthcare/legal/events: -30 to -40
- On-site only: -25

**Experience Penalties (not hard filters):**
- 0-2 years: no penalty
- 3 years: light penalty (-15)
- 4-5 years: moderate penalty (-25)
- 6+ years: strong penalty (-40)

Analyst/operations roles are scored despite higher experience requirements, allowing good fits through.

## Sorting Priority

Application plan is sorted by:
1. Should apply? (Apply > Maybe > No)
2. Priority level (High > Medium > Low)
3. Remote positions first
4. Easy apply positions first
5. Realistic fit score (Low stretch > Medium > High)
6. Overall fit score
7. Salary

## Technologies Used

- **Language:** Python 3
- **APIs:** Adzuna job listings
- **Data:** CSV, YAML
- **PDF:** fpdf2
- **Tools:** Workflow automation, job matching, scoring

## Future Improvements

- Web dashboard for job tracking
- Browser autofill integration
- SQL database support
- AI resume tailoring
<<<<<<< HEAD
- International job recommendation engine
- Improve automation workflows
=======
- Slack/email notifications
- Interview scheduling helper
>>>>>>> c926082 (Phase 1 job bot web app with Streamlit and Handshake support)
