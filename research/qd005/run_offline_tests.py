"""Run existing Python regressions with a real entry file for macOS spawn.

This also blocks Python socket connections in spawned workers, which reimport
this file as __mp_main__. Existing mocked launchers are fixtures, not app starts.
"""
from pathlib import Path
import socket
import sys
import unittest


def offline(*args, **kwargs):
    raise AssertionError("Network disabled during QD005 offline verification")


socket.create_connection = offline
socket.socket.connect = offline
socket.socket.connect_ex = offline
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    raise SystemExit(not result.wasSuccessful())
