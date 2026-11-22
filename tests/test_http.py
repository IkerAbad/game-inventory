# -*- coding: utf-8 -*-
"""HTTP helper tests with simulated responses (no real requests)."""

import os
import sys
import unittest
import urllib.error
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import inventory.network as net
from inventory.network import _json_get, http_get


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b"hello"


class HttpTests(unittest.TestCase):
    def setUp(self):
        net._NET.update({"last": {}, "failures": {}, "streak": 0, "n": 0, "down": False})
        sleeper = mock.patch("inventory.network.time.sleep")
        sleeper.start()
        self.addCleanup(sleeper.stop)

    def test_success(self):
        with mock.patch("inventory.network.urllib.request.urlopen",
                        return_value=FakeResponse()):
            self.assertEqual(http_get("https://example.com/x"), (200, "hello"))
        self.assertEqual(net._NET["n"], 1)

    def test_404_is_not_a_failure(self):
        error = urllib.error.HTTPError("https://example.com/x", 404, "Not Found", {}, None)
        with mock.patch("inventory.network.urllib.request.urlopen", side_effect=error):
            self.assertEqual(http_get("https://example.com/x"), (404, ""))
        self.assertEqual(net._NET["failures"].get("example.com", 0), 0)

    def test_repeated_500_blocks_the_host(self):
        error = urllib.error.HTTPError("https://example.com/x", 500, "Server Error", {}, None)
        with mock.patch("inventory.network.urllib.request.urlopen", side_effect=error):
            for _ in range(4):
                http_get("https://example.com/x")
            self.assertIsNone(http_get("https://example.com/x"))
        self.assertGreaterEqual(net._NET["failures"]["example.com"], 4)

    def test_three_exceptions_mark_the_network_down(self):
        error = urllib.error.URLError("no network")
        with mock.patch("inventory.network.urllib.request.urlopen", side_effect=error):
            for _ in range(3):
                http_get("https://example.com/x")
            self.assertTrue(net._NET["down"])
            self.assertIsNone(http_get("https://example.com/x"))

    def test_request_budget(self):
        net._NET["n"] = net.MAX_REQUESTS
        with mock.patch("inventory.network.urllib.request.urlopen") as urlopen:
            self.assertIsNone(http_get("https://example.com/x"))
            urlopen.assert_not_called()

    def test_json_get(self):
        with mock.patch("inventory.network.http_get",
                        return_value=(200, '{"a": 1}')):
            self.assertEqual(_json_get("https://example.com/x"), {"a": 1})
        with mock.patch("inventory.network.http_get", return_value=(200, "not json")):
            self.assertIsNone(_json_get("https://example.com/x"))
        with mock.patch("inventory.network.http_get", return_value=(500, "")):
            self.assertIsNone(_json_get("https://example.com/x"))


if __name__ == "__main__":
    unittest.main()
