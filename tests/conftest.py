import sys
from pathlib import Path

# The build scripts import each other from scripts/, which isn't a package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from hypothesis import settings  # noqa: E402

# The tests check results, not speed; on a busy machine some examples run past Hypothesis's 200 ms default
settings.register_profile("no_deadline", deadline=None)
settings.load_profile("no_deadline")
