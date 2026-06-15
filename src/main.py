#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
import helpers
import scorer


def parse_args():
    parser = argparse.ArgumentParser(description="Job Assistant CLI")
    parser.add_argument("--next-batch", action="store_true", help="Skip all previously seen and reviewed jobs aggressively")
    parser.add_argument("--mark-reviewed", action="store_true", help="Mark current application plan jobs as reviewed")
    parser.add_argument("--mark-applied", action="store_true", help="Mark current application plan jobs as applied")
    parser.add_argument("--cleanup", action="store_true", help="Clean generated files")
    parser.add_argument("--cleanup-type", choices=["cover_letters", "data", "all"], default="all", help="Cleanup target")
    parser.add_argument("--older-than", type=int, default=None, help="Only clean files older than this many days")
    parser.add_argument("--archive", action="store_true", help="Archive files instead of deleting during cleanup")
    parser.add_argument("--archive-current", action="store_true", help="Archive current application_plan.xlsx before generating a fresh batch")
    parser.add_argument("--confirm", action="store_true", help="Confirm cleanup or marking actions")
    return parser.parse_args()


def print_job_sourcing_summary(total_fetched, total_filtered, duplicate_skipped, reviewed_skipped, applied_skipped, final_jobs, fresh_unseen):
    print("\n📋 JOB SOURCING SUMMARY:")
    print(f"  📥 total fetched: {total_fetched}")
    print(f"  ✂️  filtered out: {total_filtered}")
    print(f"  🧩 duplicate skipped: {duplicate_skipped}")
    print(f"  👀 reviewed skipped: {reviewed_skipped}")
    print(f"  ✅ applied skipped: {applied_skipped}")
    print(f"  🆕 fresh unseen jobs remaining: {fresh_unseen}")
    print(f"  ✅ final jobs remaining: {final_jobs}\n")


def generate_application_plan(jobs, resume_data, config):
    plan_rows = []
    cover_letters_folder = helpers.ensure_cover_letters_folder()
    daily_target = config.get("daily_target_results", 20)

    for job in jobs:
        interview_prob, reason_to_apply = scorer.calculate_interview_probability(job, resume_data, job.get("score", 0))
        salary_status = scorer.determine_salary_status(job, config)
        realistic_fit_score = scorer.calculate_realistic_fit_score(job, resume_data, config)
        stretch_level = scorer.calculate_stretch_level(job, resume_data, config)
        next_skill = scorer.determine_next_skill_to_learn(job, resume_data)
        role_category = scorer.classify_role_category(job)
        tech_fit_reason = scorer.build_tech_fit_reason(job)
        should_apply = scorer.determine_should_apply(interview_prob, scorer.classify_experience_requirement(job, config=config), job.get("score", 0))
        cover_letter_pdf = ""
        if should_apply in ["Apply", "Maybe"]:
            cover_letter_pdf = helpers.generate_cover_letter_pdf(job, resume_data, cover_letters_folder)

        plan_rows.append({
            "company": job.get("company", ""),
            "title": job.get("title", ""),
            "link": job.get("link", ""),
            "fit_score": job.get("score", 0),
            "priority": job.get("priority", "Medium"),
            "salary_min": job.get("salary_min", ""),
            "salary_max": job.get("salary_max", ""),
            "interview_probability": interview_prob,
            "role_category": role_category,
            "tech_fit_reason": tech_fit_reason,
            "reason_to_apply": reason_to_apply,
            "realistic_fit_score": realistic_fit_score,
            "stretch_level": stretch_level,
            "next_skill_to_learn": next_skill,
            "cover_letter_pdf": cover_letter_pdf,
        })
        if len(plan_rows) >= daily_target:
            break

    csv_path = helpers.save_application_plan_csv(plan_rows)
    xlsx_path = helpers.save_application_plan_xlsx(plan_rows)
    print(f"✓ Saved application plan: {csv_path}")
    print(f"✓ Saved styled workbook: {xlsx_path}")
    return plan_rows


def run_main(next_batch=False, archive_current=False):
    config = helpers.load_config()
    resume_data = helpers.extract_resume_data()
    if archive_current:
        archived_path = helpers.archive_current_application_plan()
        if archived_path:
            print(f"✓ Archived current plan to: {archived_path}")
    if next_batch:
        print("➡️ Next-batch mode: aggressively skipping seen, reviewed, and applied company jobs.")
    adzuna_id = config.get("adzuna_app_id")
    adzuna_key = config.get("adzuna_app_key")
    country = config.get("country", "us")
    results_per_search = config.get("results_per_search", 50)
    results_pages = config.get("results_pages", 3)
    locations = config.get("locations") or [config.get("location", "Denver, CO")]
    if "remote" not in [loc.lower() for loc in locations]:
        locations.append("remote")

    if adzuna_id and adzuna_key:
        jobs = helpers.fetch_real_jobs_adzuna(
            adzuna_id,
            adzuna_key,
            country=country,
            locations=locations,
            results_per_search=results_per_search,
            pages=results_pages,
        )
    else:
        print("⚠️ Missing Adzuna credentials. Using sample fallback jobs.")
        jobs = helpers.fetch_real_jobs_fallback()

    total_fetched = len(jobs)
    applied_entries = helpers.load_applied_jobs()
    applied_entries.extend(helpers.load_applied_from_plan())
    applied_companies = helpers.load_applied_companies()
    reviewed_entries = helpers.load_reviewed_jobs()
    seen_entries = helpers.load_seen_jobs()

    def apply_filters(jobs_to_filter, title_similarity_threshold=0.90):
        filtered, stats = helpers.filter_jobs(jobs_to_filter, config)
        filtered, applied_skipped, applied_company_skipped = helpers.filter_applied_jobs(filtered, applied_entries, applied_companies)
        filtered, reviewed_skipped = helpers.filter_reviewed_jobs(filtered, reviewed_entries)
        filtered, seen_skipped = helpers.filter_seen_jobs(filtered, seen_entries, allow_seen=False)
        filtered, duplicate_skipped = helpers.filter_duplicates(filtered, title_similarity_threshold=title_similarity_threshold)
        return filtered, stats, applied_skipped, applied_company_skipped, reviewed_skipped, seen_skipped, duplicate_skipped

    filtered_jobs, stats, applied_skipped, applied_company_skipped, reviewed_skipped, seen_skipped, duplicate_skipped = apply_filters(jobs)
    fresh_unseen = len(filtered_jobs)

    if fresh_unseen < 15:
        print("➕ Expanding search criteria with adjacent keywords...")
        expanded_keywords = helpers.expand_search_keywords(config)
        jobs = helpers.fetch_real_jobs_adzuna(adzuna_id, adzuna_key, country=country, locations=locations, results_per_search=results_per_search, keywords=expanded_keywords)
        total_fetched = len(jobs)
        filtered_jobs, stats, applied_skipped, applied_company_skipped, reviewed_skipped, seen_skipped, duplicate_skipped = apply_filters(jobs)
        fresh_unseen = len(filtered_jobs)

    if not filtered_jobs:
        print("\nNo fresh jobs found. Expanding search criteria...")
        expanded_keywords = helpers.expand_search_keywords(config)
        jobs = helpers.fetch_real_jobs_adzuna(adzuna_id, adzuna_key, country=country, locations=locations, results_per_search=results_per_search, keywords=expanded_keywords)
        total_fetched = len(jobs)
        filtered_jobs, stats, applied_skipped, applied_company_skipped, reviewed_skipped, seen_skipped, duplicate_skipped = apply_filters(jobs, title_similarity_threshold=0.80)
        fresh_unseen = len(filtered_jobs)
        if not filtered_jobs:
            print("\n❌ No jobs remain after filtering.")
            print_job_sourcing_summary(total_fetched, total_fetched - len(filtered_jobs), duplicate_skipped, reviewed_skipped, applied_skipped + applied_company_skipped, len(filtered_jobs), fresh_unseen)
            return []

    scored_jobs = scorer.score_jobs(filtered_jobs, config.get("keywords"), config)
    for job in scored_jobs:
        if not job.get("job_id"):
            job["job_id"] = helpers.generate_job_id(job.get("company"), job.get("title"))

    print(f"\n📊 Final job count: {len(scored_jobs)}")
    helpers.save_results(scored_jobs)
    plan_rows = generate_application_plan(scored_jobs, resume_data, config)
    new_seen = helpers.append_seen_jobs(scored_jobs)
    if new_seen:
        print(f"✓ Added {new_seen} new jobs to {helpers.SEEN_JOBS_FILE}")
    print_job_sourcing_summary(total_fetched, total_fetched - len(filtered_jobs), duplicate_skipped, reviewed_skipped, applied_skipped + applied_company_skipped, len(scored_jobs), fresh_unseen)
    return scored_jobs


def run_cleanup(args):
    cleanup_args = []
    if args.cleanup_type:
        cleanup_args.append(f"--type={args.cleanup_type}")
    if args.older_than is not None:
        cleanup_args.append(f"--older-than={args.older_than}")
    if args.archive:
        cleanup_args.append("--archive")
    if args.confirm:
        cleanup_args.append("--confirm")
    files = helpers.cleanup_generated_files(cleanup_args)
    if not files:
        print("✓ Nothing to clean or no files matched the criteria.")
        return
    if not args.confirm:
        print("Files that would be deleted or archived:")
        for item in files:
            print(f"  - {item}")
        print("Run again with --confirm to execute cleanup.")
    else:
        print(f"✓ Cleaned {len(files)} files.")


def run_mark_applied():
    added = helpers.mark_applied_companies()
    if added:
        print(f"✓ Marked {added} new company/title combinations as applied.")
    else:
        print("No new applied companies were added.")


def run_mark_reviewed():
    added = helpers.mark_reviewed_jobs()
    if added:
        print(f"✓ Marked {added} jobs as reviewed.")
    else:
        print("No new reviewed jobs were added.")


def main():
    args = parse_args()
    if args.cleanup:
        run_cleanup(args)
        return
    if args.mark_applied:
        run_mark_applied()
        return
    if args.mark_reviewed:
        run_mark_reviewed()
        return
    print("\n🔍 Job Search Assistant - REAL Job Listings\n")
    run_main(next_batch=args.next_batch, archive_current=args.archive_current)


if __name__ == "__main__":
    main()
