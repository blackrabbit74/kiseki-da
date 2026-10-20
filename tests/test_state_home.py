"""The installer and the runtime resolve the state directory with the same rule.

installer/util.kiseki_home() and the runtime's store.kiseki_da_home() are separate on purpose (the installer
must not import the runtime before it knows which source it installs). This test keeps them identical.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from installer import util


PLUGIN = Path(__file__).resolve().parents[1] / "plugins" / "kiseki-da"
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))
from core.ctx import store  # noqa: E402


class StateHomeTest(unittest.TestCase):
    def test_installer_and_runtime_resolve_the_same_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = Path(tmp) / "home"
            fake_home.mkdir()
            cases = (None, str(Path(tmp) / "abs"), "~/custom-kiseki", "relative/dir", str(Path(tmp) / "a" / ".." / "b"))
            for value in cases:
                env = {"HOME": str(fake_home), "PA_HOME": str(Path(tmp) / "legacy")}
                if value is not None:
                    env["KISEKI_DA_HOME"] = value
                with self.subTest(value=value), mock.patch.dict(os.environ, env, clear=False):
                    if value is None:
                        os.environ.pop("KISEKI_DA_HOME", None)
                    self.assertEqual(util.kiseki_home(), store.kiseki_da_home())
                    # the legacy variable never moves the active state directory
                    self.assertNotEqual(store.kiseki_da_home(), (Path(tmp) / "legacy").resolve())


if __name__ == "__main__":
    unittest.main()
