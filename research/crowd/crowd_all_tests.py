"""Run EVERY test file in the repo (each as its own process, like the wheel study did) and print PASS/FAIL per file.   python research/crowd/crowd_all_tests.py"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
files = sorted(p for p in (ROOT / "research").rglob("test*.py"))
bad = 0
for f in files:
    r = subprocess.run([sys.executable, str(f)], capture_output=True, text=True, cwd=ROOT, timeout=900)
    last = (r.stdout.strip().splitlines() or [""])[-1][:90]
    print(("PASS" if r.returncode == 0 else "FAIL"), f.relative_to(ROOT), "|", last)
    bad += r.returncode != 0
print(f"{len(files)} test files, {bad} failing")
sys.exit(1 if bad else 0)
