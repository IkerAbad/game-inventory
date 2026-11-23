# -*- coding: utf-8 -*-
"""The offline mode must work without opening a network socket."""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from inventory.cli import main
from inventory.i18n import set_lang


def fake_game(name, gb):
    return {"name": name, "gb": gb, "days": 3, "unit": "C:",
            "path": "C:\\" + name, "duplicate": False}


class FakeWorkbook:
    """Minimal workbook so this test runs without openpyxl."""

    def save(self, path):
        with open(path, "wb") as f:
            f.write(b"stub")


class OfflineSocketTests(unittest.TestCase):
    def setUp(self):
        set_lang("en")

    def tearDown(self):
        set_lang("en")

    def test_offline_never_opens_a_socket(self):
        def blocked(*args, **kwargs):
            raise AssertionError("network access attempted")

        with tempfile.TemporaryDirectory() as d:
            data_dir = os.path.join(d, "data")
            os.makedirs(data_dir)
            paths = {
                "HOURS_JSON": os.path.join(data_dir, "hours.json"),
                "WISHLIST_JSON": os.path.join(data_dir, "wishlist.json"),
                "COMPLETED_JSON": os.path.join(data_dir, "completed.json"),
                "PLAYING_JSON": os.path.join(data_dir, "playing.json"),
                "CONFIG_JSON": os.path.join(data_dir, "config.json"),
            }
            with open(paths["HOURS_JSON"], "w", encoding="utf-8") as f:
                json.dump({"game": 10.0}, f)
            out = os.path.join(d, "out.xlsx")
            with mock.patch.multiple("inventory.cli", DATA_DIR=data_dir, **paths), \
                 mock.patch("inventory.cli.scan_games",
                            return_value=([fake_game("Game", 1.0)], [])), \
                 mock.patch("inventory.cli.build_workbook",
                            return_value=(FakeWorkbook(), 10.0,
                                          [["2026-11-23", "1", "1.0", "10.0"]])), \
                 mock.patch("inventory.cli.autocomplete") as autocomplete, \
                 mock.patch("socket.socket", side_effect=blocked), \
                 mock.patch("socket.create_connection", side_effect=blocked):
                with redirect_stdout(io.StringIO()):
                    rc = main(["--offline", "--keep", "--output", out])
                autocomplete.assert_not_called()
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()
