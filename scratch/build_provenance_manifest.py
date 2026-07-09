"""Build a cryptographic provenance manifest of the repository: a SHA-256 of every
git-tracked file plus a single root hash. Combined with the GitHub commit
timestamp (server-recorded, not forgeable) this is an immutable, dated proof of
authorship — anyone can later verify the exact content that existed on this date.

Run: python scratch/build_provenance_manifest.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import subprocess

EXCLUDE = {"provenance_manifest.sha256", "PROVENANCE.md"}
files = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split("\n")
files = sorted(f for f in files if f and f not in EXCLUDE)

lines = []
for f in files:
    try:
        h = hashlib.sha256(open(f, "rb").read()).hexdigest()
    except OSError:
        continue
    lines.append(f"{h}  {f}")

manifest = "\n".join(lines) + "\n"
open("provenance_manifest.sha256", "w", encoding="utf-8", newline="\n").write(manifest)
root = hashlib.sha256(manifest.encode()).hexdigest()

commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
print("date (UTC):", dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
print("files hashed:", len(lines))
print("ROOT SHA-256:", root)
print("git commit  :", commit)
