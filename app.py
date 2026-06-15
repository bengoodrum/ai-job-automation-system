"""Streamlit dashboard for the Job Assistant (Phase 1).

Run with:  streamlit run app.py

This is an additive UI layer. It reuses the existing search/scoring pipeline and
the shared service modules. It never auto-applies and performs no login/scraping
bypass. Handshake jobs are imported manually (paste only).
"""

import sys
import logging
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import services  # noqa: E402
import status_store  # noqa: E402
import applications  # noqa: E402
from sources import handshake  # noqa: E402

logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="Job Assistant", page_icon="🧭", layout="wide")

ROLE_CATEGORIES = {
    "Project Coordinator": ["project coordinator", "program coordinator", "technical project"],
    "Operations": ["operations", "ops ", "operations coordinator", "operations associate"],
    "Business Analyst": ["business analyst", "business systems analyst", "systems analyst"],
    "AI Operations": ["ai operations", "ai ops", "ai operations associate"],
    "Implementation Specialist": ["implementation specialist", "implementation analyst", "implementation"],
    "Product Ops": ["product operations", "product ops"],
    "Workflow Automation": ["workflow automation", "automation specialist", "workflow"],
}


def _matches_categories(job, selected):
    if not selected:
        return True
    text = f"{job.get('title','')} {job.get('description','')}".lower()
    for cat in selected:
        if any(kw in text for kw in ROLE_CATEGORIES.get(cat, [])):
            return True
    return False


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_all_jobs():
    """Combine cached search results + Handshake imports, merged with status."""
    jobs = services.load_results_cache()
    seen_ids = {j["id"] for j in jobs}
    for hs_job in handshake.load_handshake_jobs():
        if hs_job["id"] not in seen_ids:
            jobs.append(hs_job)
            seen_ids.add(hs_job["id"])
    statuses = status_store.load_statuses()
    for job in jobs:
        st_entry = statuses.get(job["id"])
        if st_entry:
            job["status"] = st_entry.get("status", job.get("status", "Seen"))
            job["notes"] = st_entry.get("notes", job.get("notes", ""))
    return jobs


def sidebar_controls():
    st.sidebar.header("Search & Filters")
    if st.sidebar.button("🔎 Run job search", use_container_width=True, type="primary"):
        with st.spinner("Running Adzuna search pipeline... this may take a moment."):
            try:
                results = services.run_search()
                st.session_state["last_run_count"] = len(results)
                st.sidebar.success(f"Search complete: {len(results)} jobs.")
            except Exception as exc:
                st.sidebar.error(f"Search failed: {exc}")

    st.sidebar.caption("Live search uses the Adzuna API (same as the CLI).")
    st.sidebar.divider()

    st.sidebar.subheader("Sources")
    st.sidebar.caption("LinkedIn / Indeed are planned for Phase 2.")
    source_filter = st.sidebar.multiselect(
        "Show sources", options=["Adzuna", "Handshake"], default=["Adzuna", "Handshake"]
    )

    st.sidebar.subheader("Role categories")
    categories = st.sidebar.multiselect("Filter by role category", options=list(ROLE_CATEGORIES.keys()))

    st.sidebar.subheader("Work type")
    remote_types = st.sidebar.multiselect(
        "Remote type", options=["remote", "hybrid", "on-site", "unknown"],
        default=["remote", "hybrid", "on-site", "unknown"],
    )

    min_salary = st.sidebar.number_input("Minimum salary ($)", min_value=0, value=0, step=5000)
    exclusions = st.sidebar.text_input("Exclusion keywords (comma separated)")

    return {
        "sources": source_filter,
        "categories": categories,
        "remote_types": remote_types,
        "min_salary": min_salary,
        "exclusions": [e.strip().lower() for e in exclusions.split(",") if e.strip()],
    }


def apply_filters(jobs, controls):
    filtered = []
    for job in jobs:
        if controls["sources"] and job.get("source") not in controls["sources"]:
            continue
        if not _matches_categories(job, controls["categories"]):
            continue
        if controls["remote_types"] and job.get("remote_type", "unknown") not in controls["remote_types"]:
            continue
        if controls["min_salary"]:
            sal = _to_float(job.get("salary_min"))
            if sal is not None and sal < controls["min_salary"]:
                continue
        if controls["exclusions"]:
            text = f"{job.get('title','')} {job.get('description','')}".lower()
            if any(ex in text for ex in controls["exclusions"]):
                continue
        filtered.append(job)
    return filtered


def handshake_panel(current_jobs):
    with st.expander("➕ Import a Handshake job (manual paste only)"):
        st.caption(
            "Paste a job you are authorized to view. This does not log in, scrape, "
            "or bypass any Handshake protection, and never auto-applies."
        )
        col1, col2 = st.columns(2)
        with col1:
            hs_title = st.text_input("Title", key="hs_title")
            hs_company = st.text_input("Company", key="hs_company")
            hs_location = st.text_input("Location", key="hs_location")
        with col2:
            hs_url = st.text_input("Handshake job URL", key="hs_url")
            hs_salary_min = st.text_input("Salary min (optional)", key="hs_salary_min")
            hs_salary_max = st.text_input("Salary max (optional)", key="hs_salary_max")
        hs_text = st.text_area("Paste full job description", key="hs_text", height=180)
        if st.button("Import Handshake job"):
            job, imported, message = handshake.import_handshake_job(
                pasted_text=hs_text, url=hs_url, title=hs_title, company=hs_company,
                location=hs_location, salary_min=hs_salary_min, salary_max=hs_salary_max,
                existing_jobs=current_jobs,
            )
            if imported:
                st.success(f"{message} ({job.get('title')} @ {job.get('company')})")
            else:
                st.warning(message)


def status_table(jobs):
    st.subheader("Results")
    if not jobs:
        st.info("No jobs yet. Click **Run job search** or import a Handshake job.")
        return

    import pandas as pd

    display_cols = ["score", "title", "company", "location", "source", "remote_type",
                    "salary_min", "url", "date_found", "status", "notes", "id"]
    rows = [{c: job.get(c, "") for c in display_cols} for job in jobs]
    df = pd.DataFrame(rows)

    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": None,
            "url": st.column_config.LinkColumn("URL"),
            "status": st.column_config.SelectboxColumn(
                "Status", options=status_store.VALID_STATUSES, required=True
            ),
            "notes": st.column_config.TextColumn("Notes"),
            "score": st.column_config.NumberColumn("Score"),
        },
        disabled=["score", "title", "company", "location", "source", "remote_type",
                  "salary_min", "url", "date_found"],
        key="results_editor",
    )

    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("💾 Save status changes"):
            original = {r["id"]: r for r in rows}
            saved = 0
            for _, row in edited.iterrows():
                job_id = row["id"]
                orig = original.get(job_id, {})
                if str(row.get("status")) != str(orig.get("status")) or \
                   str(row.get("notes")) != str(orig.get("notes")):
                    status_store.set_status(
                        job_id, status=row.get("status"), notes=row.get("notes"),
                        company=row.get("company", ""), title=row.get("title", ""),
                        url=row.get("url", ""),
                    )
                    saved += 1
            st.success(f"Saved {saved} status change(s).")
    with col_b:
        csv_bytes = df.drop(columns=["id"]).to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Export CSV", data=csv_bytes,
                           file_name="job_results.csv", mime="text/csv")


def materials_panel(jobs):
    st.subheader("Generate tailored materials")
    if not jobs:
        return
    labels = {f"{j.get('title','?')} @ {j.get('company','?')}  [{j.get('source','')}]": j for j in jobs}
    choice = st.selectbox("Select a job", options=list(labels.keys()))
    selected = labels.get(choice)
    if not selected:
        return
    st.caption("Resume tailoring only reorders/emphasizes your real bullets — it never invents experience.")
    if st.button("📝 Generate resume + cover letter"):
        with st.spinner("Generating tailored .docx files..."):
            try:
                outputs = applications.generate_application(selected)
            except Exception as exc:
                st.error(f"Generation failed: {exc}")
                return
        st.success(f"Saved to: {outputs.get('folder')}")
        for key, label in [("resume_docx", "Download tailored resume (.docx)"),
                           ("cover_letter_docx", "Download cover letter (.docx)")]:
            path = outputs.get(key)
            if path and Path(path).exists():
                with open(path, "rb") as f:
                    st.download_button(label, data=f.read(), file_name=Path(path).name,
                                       mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                       key=f"dl_{key}")
        with st.expander("Cover letter preview"):
            st.text(outputs.get("cover_letter_text", ""))
        with st.expander("Keyword match report"):
            st.text(outputs.get("keyword_report_text", ""))


def main():
    st.title("🧭 Job Assistant")
    st.caption("Find, score, organize, and prepare applications. No auto-apply. Local only.")

    controls = sidebar_controls()
    all_jobs = load_all_jobs()
    handshake_panel(all_jobs)
    filtered = apply_filters(all_jobs, controls)
    st.write(f"Showing **{len(filtered)}** of {len(all_jobs)} jobs.")
    status_table(filtered)
    materials_panel(filtered)


if __name__ == "__main__":
    main()
