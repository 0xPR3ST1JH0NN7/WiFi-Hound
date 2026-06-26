import pathlib
import sys

# Make the project root importable when running pytest from anywhere.
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
