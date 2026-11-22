"""Check that the English and Spanish translations match.

Verifies that both languages define the same keys, that the placeholders of each
key are identical and that no dictionary literal repeats a key.
"""

import ast
import os
import string
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from inventory.i18n import TEXT


def placeholders(text):
    """Named placeholders of a format string, ignoring literal braces."""
    found = set()
    for _, field, _, _ in string.Formatter().parse(text):
        if field:
            found.add(field.split(".")[0].split("[")[0])
    return found


def compare(english, spanish):
    """Return a list of problems between the two translation dictionaries."""
    problems = []
    for key in sorted(set(english) - set(spanish)):
        problems.append("missing in es: %s" % key)
    for key in sorted(set(spanish) - set(english)):
        problems.append("missing in en: %s" % key)
    for key in sorted(set(english) & set(spanish)):
        en_fields = placeholders(str(english[key]))
        es_fields = placeholders(str(spanish[key]))
        if en_fields != es_fields:
            problems.append("%s: placeholders %s != %s"
                            % (key, sorted(en_fields), sorted(es_fields)))
    return problems


def duplicate_keys(path):
    """Duplicate keys inside any dictionary literal of the file."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), path)
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            seen = set()
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    if key.value in seen:
                        problems.append("%s: duplicate key %r at line %d"
                                        % (path, key.value, key.lineno))
                    seen.add(key.value)
    return problems


def main():
    problems = compare(TEXT["en"], TEXT["es"])
    problems += duplicate_keys("inventory/i18n.py")
    if problems:
        for problem in problems:
            print("FAIL: " + problem)
        return 1
    print("OK i18n: %d keys in both languages" % len(TEXT["en"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
