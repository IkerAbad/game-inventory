"""Text normalization shared by the package."""

import re


def normalize(name):
    """Lowercase, keep letters and digits, collapse the rest into single spaces."""
    name = re.sub(r"[^a-z0-9]+", " ", str(name).lower().strip())
    return re.sub(r"\s+", " ", name).strip()
