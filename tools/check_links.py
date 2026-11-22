"""Check that relative links in the Markdown docs point to existing files."""

import glob
import os
import re
import sys

LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SKIP = ("http://", "https://", "mailto:", "#", "tel:")


def check_file(path):
    """Return the broken relative targets of one Markdown file."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    broken = []
    for target in LINK.findall(text):
        target = target.strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        target = target.split("#", 1)[0].split(" ", 1)[0]
        if not target or target.startswith(SKIP):
            continue
        full = os.path.normpath(os.path.join(os.path.dirname(path), target))
        if not os.path.exists(full):
            broken.append((path, target))
    return broken


def main():
    files = sorted(glob.glob("*.md")) + sorted(glob.glob("docs/*.md"))
    broken = []
    for path in files:
        broken.extend(check_file(path))
    if broken:
        for path, target in broken:
            print("FAIL: %s -> %s" % (path, target))
        return 1
    print("OK links: %d Markdown files" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
