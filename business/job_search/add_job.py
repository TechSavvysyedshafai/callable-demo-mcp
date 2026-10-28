"""Score a job and append it to job_tracker.csv.

Usage: python3 add_job.py job.json [--tracker PATH]

job.json holds the score inputs used by score.py plus these tracker fields:
  company, role, platform, location, posted, url, notes (all optional except company, role, url)
A job whose url is already in the tracker is refused, so reruns do not duplicate rows.
"""
import argparse
import csv
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import chance, fit  # noqa: E402

COLUMNS = [
    "date_found", "company", "role", "platform", "location", "posted", "url",
    "fit_score", "interview_chance", "hard_gaps", "materials", "status",
    "date_applied", "follow_up", "notes",
]
REQUIRED = ("company", "role", "url")


def existing_urls(path):
    if not os.path.exists(path):
        return set()
    with open(path, newline="") as f:
        return {row["url"] for row in csv.DictReader(f)}


def build_row(job, today=None):
    missing = [k for k in REQUIRED if not job.get(k)]
    if missing:
        raise ValueError("missing field(s): " + ", ".join(missing))
    score, _raw, _capped = fit(job)
    gaps = job.get("hard_gaps") or []
    row = {c: "" for c in COLUMNS}
    row.update({
        "date_found": today or date.today().isoformat(),
        "company": job["company"],
        "role": job["role"],
        "platform": job.get("platform", ""),
        "location": job.get("location", ""),
        "posted": job.get("posted", ""),
        "url": job["url"],
        "fit_score": round(score),
        "interview_chance": chance(score, bool(gaps)),
        "hard_gaps": "; ".join(gaps),
        "materials": job.get("materials", "none yet"),
        "status": "Found",
        "notes": job.get("notes", ""),
    })
    return row


def add_job(job, tracker, today=None):
    row = build_row(job, today)
    if row["url"] in existing_urls(tracker):
        raise ValueError("already in tracker: " + row["url"])
    new_file = not os.path.exists(tracker) or os.path.getsize(tracker) == 0
    with open(tracker, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)
    return row


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("job_json")
    parser.add_argument("--tracker", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "job_tracker.csv"))
    args = parser.parse_args(argv)
    try:
        with open(args.job_json) as f:
            job = json.load(f)
        row = add_job(job, args.tracker)
    except (OSError, ValueError, KeyError) as err:
        sys.exit("add_job: " + str(err))
    print(f"added {row['company']} - {row['role']}: fit {row['fit_score']}%, interview chance {row['interview_chance']}")


if __name__ == "__main__":
    main(sys.argv[1:])
