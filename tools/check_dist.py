"""Check the built distributions: no personal data and the expected files.

Run after `python -m build`:

    python tools/check_dist.py
"""

import glob
import os
import sys
import tarfile
import zipfile


def fail(message):
    print("FAIL: " + message)
    sys.exit(1)


def check_no_data(names, label):
    leaked = [name for name in names
              if name == "data" or name.startswith("data/") or "/data/" in name]
    if leaked:
        fail("%s contains personal data: %s" % (label, ", ".join(leaked[:5])))


def check_wheel(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    check_no_data(names, path)
    for required in ("inventory/__init__.py", "inventory/cli.py",
                     "inventory/i18n.py"):
        if required not in names:
            fail("%s is missing %s" % (path, required))
    leaked = [name for name in names if name.startswith("tools/")]
    if leaked:
        fail("%s should not ship the development tools: %s"
             % (path, ", ".join(leaked[:5])))
    print("OK wheel: %s (%d files)" % (os.path.basename(path), len(names)))


def check_sdist(path):
    with tarfile.open(path) as archive:
        names = [member.name for member in archive.getmembers()]
    check_no_data(names, path)
    for required in ("README.es.md", "CHANGELOG.md", "docs/DATA.md",
                     "tests/test_basico.py", "tools/check_all.py"):
        if not any(name.endswith(required) for name in names):
            fail("%s is missing %s" % (path, required))
    print("OK sdist: %s (%d files)" % (os.path.basename(path), len(names)))


def main():
    wheels = glob.glob(os.path.join("dist", "*.whl"))
    sdists = glob.glob(os.path.join("dist", "*.tar.gz"))
    if not wheels or not sdists:
        fail("run python -m build first: dist/ has no wheel or sdist")
    for wheel in wheels:
        check_wheel(wheel)
    for sdist in sdists:
        check_sdist(sdist)
    return 0


if __name__ == "__main__":
    sys.exit(main())
