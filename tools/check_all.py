"""Run the static repository checks in one command."""

import importlib.util
import subprocess
import sys


def checks():
    """Available checks, with pyflakes only when it is installed."""
    selected = []
    if importlib.util.find_spec("pyflakes") is not None:
        selected.append(("pyflakes", [sys.executable, "-m", "pyflakes",
                                      "inventory", "generate_inventory.py",
                                      "tests", "tools"]))
    else:
        print("skip pyflakes (install it with: pip install -e \".[dev]\")")
    selected.append(("links", [sys.executable, "tools/check_links.py"]))
    selected.append(("i18n", [sys.executable, "tools/check_i18n.py"]))
    return selected


def main(selected=None):
    selected = checks() if selected is None else selected
    failed = []
    for name, command in selected:
        print("== %s" % name)
        if subprocess.run(command).returncode:
            failed.append(name)
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("OK: %d checks" % len(selected))
    return 0


if __name__ == "__main__":
    sys.exit(main())
