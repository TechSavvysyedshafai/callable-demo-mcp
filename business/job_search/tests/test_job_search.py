import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import add_job
import score

GOOD = {"skills": 0.9, "years": 0.9, "domain": 0.9, "seniority": 0.9, "projects": 0.9, "education": 0.9}


class ScoreTests(unittest.TestCase):
    def test_no_gap_keeps_raw_score(self):
        s, raw, capped = score.fit(dict(GOOD, hard_gaps=[]))
        self.assertEqual(s, 90.0)
        self.assertFalse(capped)

    def test_hard_gap_caps_at_45(self):
        s, raw, capped = score.fit(dict(GOOD, hard_gaps=["needs 10 years"]))
        self.assertEqual(s, 45.0)
        self.assertEqual(raw, 90.0)
        self.assertTrue(capped)

    def test_low_score_with_gap_is_not_raised(self):
        low = {k: 0.1 for k in GOOD}
        s, raw, capped = score.fit(dict(low, hard_gaps=["x"]))
        self.assertEqual(s, raw)
        self.assertFalse(capped)

    def test_chance_bands(self):
        self.assertEqual(score.chance(30, False), "under 5%")
        self.assertEqual(score.chance(70, False), "20-35%")
        self.assertEqual(score.chance(70, True), "5-15%")
        self.assertEqual(score.chance(50, False), "5-15%")


class AddJobTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.tracker = os.path.join(self.dir, "t.csv")
        self.job = dict(GOOD, company="Acme", role="BA", url="https://x/1", hard_gaps=[])

    def rows(self):
        with open(self.tracker, newline="") as f:
            return list(csv.DictReader(f))

    def test_creates_file_with_header_and_row(self):
        row = add_job.add_job(self.job, self.tracker, today="2026-10-28")
        self.assertEqual(row["fit_score"], 90)
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(list(rows[0].keys()), add_job.COLUMNS)
        self.assertEqual(rows[0]["status"], "Found")

    def test_duplicate_url_refused(self):
        add_job.add_job(self.job, self.tracker)
        with self.assertRaises(ValueError):
            add_job.add_job(self.job, self.tracker)
        self.assertEqual(len(self.rows()), 1)

    def test_missing_required_field(self):
        bad = dict(self.job)
        del bad["url"]
        with self.assertRaises(ValueError):
            add_job.add_job(bad, self.tracker)

    def test_gaps_recorded_and_chance_lowered(self):
        job = dict(self.job, hard_gaps=["SQL required", "7 yrs"])
        row = add_job.add_job(job, self.tracker)
        self.assertEqual(row["fit_score"], 45)
        self.assertEqual(row["interview_chance"], "5-15%")
        self.assertEqual(row["hard_gaps"], "SQL required; 7 yrs")


if __name__ == "__main__":
    unittest.main()
