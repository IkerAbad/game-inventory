# -*- coding: utf-8 -*-
"""Tests for the repository tools: distribution and link checks."""

import io
import os
import sys
import tarfile
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools import check_all, check_dist, check_i18n, check_links, check_release


def make_wheel(path, names):
    with zipfile.ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(name, "x")


def make_sdist(path, names):
    with tarfile.open(path, "w:gz") as archive:
        for name in names:
            data = b"x"
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


class CheckDistTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dist = os.path.join(self.tmp.name, "dist")
        os.makedirs(self.dist)

    def wheel(self, names):
        path = os.path.join(self.tmp.name, "game_inventory-1.0.0-py3-none-any.whl")
        make_wheel(path, names)
        return path

    def sdist(self, names):
        path = os.path.join(self.tmp.name, "game_inventory-1.0.0.tar.gz")
        make_sdist(path, names)
        return path

    def test_good_wheel(self):
        path = self.wheel(["inventory/__init__.py", "inventory/cli.py",
                           "inventory/i18n.py"])
        with redirect_stdout(io.StringIO()) as out:
            check_dist.check_wheel(path)
        self.assertIn("OK wheel", out.getvalue())

    def test_wheel_with_data(self):
        path = self.wheel(["inventory/__init__.py", "inventory/cli.py",
                           "inventory/i18n.py", "data/hours.json"])
        with redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(SystemExit):
                check_dist.check_wheel(path)
        self.assertIn("personal data", out.getvalue())

    def test_wheel_missing_module(self):
        path = self.wheel(["inventory/__init__.py"])
        with redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(SystemExit):
                check_dist.check_wheel(path)
        self.assertIn("missing", out.getvalue())

    def test_wheel_with_tools(self):
        path = self.wheel(["inventory/__init__.py", "inventory/cli.py",
                           "inventory/i18n.py", "tools/check_all.py"])
        with redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(SystemExit):
                check_dist.check_wheel(path)
        self.assertIn("should not ship", out.getvalue())

    def test_good_sdist(self):
        path = self.sdist(["root/README.es.md", "root/CHANGELOG.md",
                           "root/docs/DATA.md", "root/tests/test_basico.py",
                           "root/tools/check_all.py"])
        with redirect_stdout(io.StringIO()) as out:
            check_dist.check_sdist(path)
        self.assertIn("OK sdist", out.getvalue())

    def test_sdist_with_data(self):
        path = self.sdist(["root/README.es.md", "root/CHANGELOG.md",
                           "root/docs/DATA.md", "root/tests/test_basico.py",
                           "root/tools/check_all.py",
                           "root/data/wishlist.json"])
        with redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(SystemExit):
                check_dist.check_sdist(path)
        self.assertIn("personal data", out.getvalue())

    def test_sdist_missing_docs(self):
        path = self.sdist(["root/README.es.md"])
        with redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(SystemExit):
                check_dist.check_sdist(path)
        self.assertIn("missing", out.getvalue())

    def test_main_without_dist(self):
        old = os.getcwd()
        os.chdir(self.tmp.name)
        try:
            with redirect_stdout(io.StringIO()) as out:
                with self.assertRaises(SystemExit):
                    check_dist.main()
        finally:
            os.chdir(old)
        self.assertIn("python -m build", out.getvalue())

    def test_main_checks_both_files(self):
        make_wheel(os.path.join(self.dist, "game.whl"),
                   ["inventory/__init__.py", "inventory/cli.py",
                    "inventory/i18n.py"])
        make_sdist(os.path.join(self.dist, "game.tar.gz"),
                   ["root/README.es.md", "root/CHANGELOG.md",
                    "root/docs/DATA.md", "root/tests/test_basico.py",
                    "root/tools/check_all.py"])
        old = os.getcwd()
        os.chdir(self.tmp.name)
        try:
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(check_dist.main(), 0)
        finally:
            os.chdir(old)
        self.assertIn("OK wheel", out.getvalue())
        self.assertIn("OK sdist", out.getvalue())


class CheckReleaseTests(unittest.TestCase):
    def test_tag_matches_version(self):
        self.assertTrue(check_release.check_tag("v1.2.3", "1.2.3"))
        self.assertFalse(check_release.check_tag("1.2.3", "1.2.3"))
        self.assertFalse(check_release.check_tag("v1.2.4", "1.2.3"))

    def test_changelog_section(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "CHANGELOG.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("# Changelog\n\n## [1.2.3] - 2026-11-23\n")
            self.assertTrue(check_release.changelog_has_version(path, "1.2.3"))
            self.assertFalse(check_release.changelog_has_version(path, "1.2.4"))
            self.assertFalse(check_release.changelog_has_version(
                os.path.join(d, "missing.md"), "1.2.3"))

    def test_main_with_real_changelogs(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(check_release.main(["v" + check_release.__version__]), 0)
        self.assertIn("OK release", out.getvalue())

    def test_main_with_wrong_tag(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(check_release.main(["v9.9.9"]), 1)
        self.assertIn("does not match", out.getvalue())

    def test_main_without_arguments(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(check_release.main([]), 2)
        self.assertIn("usage", out.getvalue())


class CheckAllTests(unittest.TestCase):
    def test_all_checks_pass(self):
        with mock.patch("tools.check_all.subprocess.run") as run:
            run.return_value.returncode = 0
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(check_all.main([("a", ["x"]), ("b", ["y"])]), 0)
        self.assertEqual(run.call_count, 2)
        self.assertIn("OK: 2 checks", out.getvalue())

    def test_one_check_fails(self):
        first = mock.Mock(returncode=0)
        second = mock.Mock(returncode=1)
        with mock.patch("tools.check_all.subprocess.run",
                        side_effect=[first, second]):
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(check_all.main([("a", ["x"]), ("b", ["y"])]), 1)
        self.assertIn("FAILED: b", out.getvalue())

    def test_pyflakes_is_included_when_installed(self):
        with mock.patch("tools.check_all.importlib.util.find_spec",
                        return_value=object()):
            names = [name for name, _ in check_all.checks()]
        self.assertEqual(names[:1], ["pyflakes"])
        self.assertIn("links", names)
        self.assertIn("i18n", names)

    def test_pyflakes_is_skipped_when_missing(self):
        with mock.patch("tools.check_all.importlib.util.find_spec",
                        return_value=None):
            with redirect_stdout(io.StringIO()) as out:
                names = [name for name, _ in check_all.checks()]
        self.assertNotIn("pyflakes", names)
        self.assertIn("skip pyflakes", out.getvalue())


class CheckI18nTests(unittest.TestCase):
    def test_placeholders(self):
        self.assertEqual(check_i18n.placeholders("Hi {name}, {n:.2f}"), {"name", "n"})
        self.assertEqual(check_i18n.placeholders("{{literal}} and {x}"), {"x"})
        self.assertEqual(check_i18n.placeholders("no fields"), set())

    def test_compare_equal(self):
        self.assertEqual(check_i18n.compare({"a": "{n}"}, {"a": "{n}"}), [])

    def test_compare_missing_and_extra(self):
        problems = check_i18n.compare({"a": "x"}, {"b": "y"})
        self.assertIn("missing in es: a", problems)
        self.assertIn("missing in en: b", problems)

    def test_compare_placeholder_mismatch(self):
        problems = check_i18n.compare({"a": "{n}"}, {"a": "{m}"})
        self.assertEqual(len(problems), 1)
        self.assertIn("placeholders", problems[0])

    def test_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "texts.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write("TEXT = {'a': '1', 'a': '2'}\n")
            problems = check_i18n.duplicate_keys(path)
        self.assertEqual(len(problems), 1)
        self.assertIn("duplicate key 'a'", problems[0])

    def test_main_is_clean(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(check_i18n.main(), 0)
        self.assertIn("OK i18n", out.getvalue())
        self.assertIn("%d keys" % len(check_i18n.TEXT["en"]), out.getvalue())

    def test_main_without_source_file(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("tools.check_i18n.ROOT", d):
                with redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(check_i18n.main(), 0)
        self.assertIn("OK i18n", out.getvalue())


class CheckLinksTests(unittest.TestCase):
    def test_reports_only_broken_relative_links(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "target.md"), "w", encoding="utf-8"):
                pass
            path = os.path.join(d, "doc.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("[ok](target.md)\n[bad](missing.md)\n")
                f.write("[web](https://example.com)\n[anchor](#top)\n")
                f.write("![image](missing.png)\n")
            broken = check_links.check_file(path)
        self.assertEqual(broken, [(path, "missing.md"), (path, "missing.png")])

    def test_main_ok_and_broken(self):
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "docs"))
            with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as f:
                f.write("[docs](docs/DATA.md)\n")
            with open(os.path.join(d, "docs", "DATA.md"), "w", encoding="utf-8") as f:
                f.write("[back](../README.md)\n")
            os.chdir(d)
            try:
                with redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(check_links.main(), 0)
                self.assertIn("OK links", out.getvalue())
                with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as f:
                    f.write("[gone](docs/GONE.md)\n")
                with redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(check_links.main(), 1)
                self.assertIn("FAIL", out.getvalue())
            finally:
                os.chdir(old)


if __name__ == "__main__":
    unittest.main()
