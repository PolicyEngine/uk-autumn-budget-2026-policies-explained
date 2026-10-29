"""Check that bun.lock here holds only package versions that policyengine-app-v2's
bun.lock holds at a commit:

    python3 site/compare_lock.py ~/PolicyEngine/policyengine-app-v2 85571f7a3

Prints each package whose version differs, and exits 1 if any does.
"""

import re
import subprocess
import sys
from pathlib import Path

ENTRY = re.compile(r'^    "[^"]+": \["((?:@[^@"]+/)?[^@"]+)@([^"]+)"', re.M)


def versions(lock):
    found = {}
    for name, version in ENTRY.findall(lock):
        found.setdefault(name, set()).add(version)
    return found


app, commit = sys.argv[1:3]
theirs = versions(subprocess.run(["git", "-C", app, "show", f"{commit}:bun.lock"],
                                 capture_output=True, text=True, check=True).stdout)
ours = versions((Path(__file__).parent / "bun.lock").read_text())
differ = {name: (sorted(v), sorted(theirs.get(name, []))) for name, v in ours.items() if not v <= theirs.get(name, set())}
for name, (here, there) in sorted(differ.items()):
    print(f"{name}: here {here}, app-v2 {there}")
print(f"{len(ours)} packages, {len(differ)} differ")
sys.exit(1 if differ else 0)
