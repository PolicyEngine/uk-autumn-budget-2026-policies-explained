import sys
from pathlib import Path

# The build scripts import each other from scripts/, which isn't a package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
