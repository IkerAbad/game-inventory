# -*- coding: utf-8 -*-
"""End-to-end test of the GAME_INVENTORY_DATA override, in a subprocess."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class EnvironmentDataTests(unittest.TestCase):
    def run_check(self, data_dir):
        env = dict(os.environ, GAME_INVENTORY_DATA=data_dir)
        return subprocess.run(
            [sys.executable, "-m", "inventory", "--check-data"],
            cwd=ROOT, env=env, capture_output=True, text=True)

    def test_valid_folder(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "hours.json"), "w", encoding="utf-8") as f:
                json.dump({"game": 10.0}, f)
            proc = self.run_check(d)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Hours: 1 games", proc.stdout)

    def test_invalid_folder(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "hours.json"), "w", encoding="utf-8") as f:
                json.dump([], f)
            proc = self.run_check(d)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("ABORTED", proc.stdout)

    def test_language_from_environment(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "hours.json"), "w", encoding="utf-8") as f:
                json.dump({"game": 10.0}, f)
            env = dict(os.environ, GAME_INVENTORY_DATA=d,
                       GAME_INVENTORY_LANG="es")
            proc = subprocess.run(
                [sys.executable, "-m", "inventory", "--check-data"],
                cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("COMPROBACION DE DATOS", proc.stdout)
        self.assertIn("Avisos:", proc.stdout)


if __name__ == "__main__":
    unittest.main()
