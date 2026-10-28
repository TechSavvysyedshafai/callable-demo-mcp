"""Fit score for a job posting. Usage: python3 score.py jobs.json

jobs.json is a list of objects:
  {"company": ..., "role": ..., "skills": 0-1, "years": 0-1, "domain": 0-1,
   "seniority": 0-1, "projects": 0-1, "education": 0-1, "hard_gaps": ["..."]}
Weights follow SKILL.md. Any hard gap caps the total at 45%.
"""
import json
import sys

WEIGHTS = {"skills": 3, "years": 2, "domain": 2, "seniority": 2, "projects": 1, "education": 1}
HARD_GAP_CAP = 45.0


def fit(job):
    total = sum(WEIGHTS.values())
    raw = sum(WEIGHTS[k] * float(job[k]) for k in WEIGHTS) / total * 100
    capped = bool(job.get("hard_gaps")) and raw > HARD_GAP_CAP
    return round(min(raw, HARD_GAP_CAP) if job.get("hard_gaps") else raw, 1), round(raw, 1), capped


def chance(score, has_gap):
    if score < 40:
        return "under 5%"
    if score >= 65 and not has_gap:
        return "20-35%"
    return "5-15%"


def main(path):
    try:
        with open(path) as f:
            jobs = json.load(f)
        lines = []
        for j in jobs:
            score, raw, capped = fit(j)
            note = f" (raw {raw}, capped by: {'; '.join(j['hard_gaps'])})" if capped else ""
            lines.append(f"{j['company']} - {j['role']}: fit {score}%{note}; interview chance {chance(score, bool(j.get('hard_gaps')))}")
    except OSError as err:
        sys.exit(f"score: cannot read {path}: {err}")
    except KeyError as err:
        sys.exit(f"score: a job is missing the field {err}")
    print("\n".join(lines))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
