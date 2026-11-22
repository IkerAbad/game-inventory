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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools import check_dist, check_links


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

    def test_good_sdist(self):
        path = self.sdist(["root/README.es.md", "root/CHANGELOG.md",
                           "root/docs/DATA.md", "root/tests/test_basico.py"])
        with redirect_stdout(io.StringIO()) as out:
            check_dist.check_sdist(path)
        self.assertIn("OK sdist", out.getvalue())

    def test_sdist_with_data(self):
        path = self.sdist(["root/README.es.md", "root/CHANGELOG.md",
                           "root/docs/DATA.md", "root/tests/test_basico.py",
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
                    "root/docs/DATA.md", "root/tests/test_basico.py"])
        old = os.getcwd()
        os.chdir(self.tmp.name)
        try:
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(check_dist.main(), 0)
        finally:
            os.chdir(old)
        self.assertIn("OK wheel", out.getvalue())
        self.assertIn("OK sdist", out.getvalue())


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
