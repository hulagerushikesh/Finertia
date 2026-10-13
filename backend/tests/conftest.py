"""Make the backend modules importable from the tests directory."""

import os
import sys
from pathlib import Path

# Route tests replace get_db with a fake, so the shared rate limiter must not
# try to reach Firestore through it; the in-process limiter is what they test.
os.environ.setdefault("RATE_LIMIT_STORE", "memory")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
