"""Check that a release tag matches the package version and the changelogs."""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from inventory import __version__


def check_tag(tag, version):
    return tag == "v" + version


def changelog_has_version(path, version):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return False
    return re.search(r"^## \[%s\]" % re.escape(version), text, re.M) is not None


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python tools/check_release.py vX.Y.Z")
        return 2
    tag = args[0]
    problems = []
    if not check_tag(tag, __version__):
        problems.append("tag %s does not match version %s" % (tag, __version__))
    for name in ("CHANGELOG.md", "CHANGELOG.es.md"):
        if not changelog_has_version(os.path.join(ROOT, name), __version__):
            problems.append("%s has no section for %s" % (name, __version__))
    if problems:
        for problem in problems:
            print("FAIL: " + problem)
        return 1
    print("OK release: %s" % tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
