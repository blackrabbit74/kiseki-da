from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from installer.hosts import HostManager


class CodexInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        patch = mock.patch.dict(os.environ, {"CODEX_HOME": str(self.root)})
        patch.start()
        self.addCleanup(patch.stop)

    def inventory(self, rows, config=""):
        (self.root / "config.toml").write_text(config, encoding="utf-8")
        def run(argv):
            value = {"marketplaces": rows} if "marketplace" in argv else {"installed": []}
            return subprocess.CompletedProcess(argv, 0, json.dumps(value), "")
        with mock.patch.object(HostManager, "run", side_effect=run):
            return HostManager("codex").inventory()

    def test_current_cli_local_source_comes_from_registered_config(self):
        result = self.inventory(
            [{"name": "kiseki-da", "root": "C:\\Users\\利用者\\kiseki-da"}],
            "[marketplaces.kiseki-da]\nsource_type = 'local'\n"
            "source = 'C:\\Users\\利用者\\kiseki-da'\n",
        )
        self.assertTrue(result.marketplace)
        self.assertEqual(result.marketplace_fingerprint,
                         {"sourceType": "local", "source": "C:\\Users\\利用者\\kiseki-da"})

    def test_current_cli_git_source_preserves_ref_instead_of_using_cache_root(self):
        result = self.inventory(
            [{"name": "kiseki-da", "root": "/cache/marketplaces/kiseki-da"}],
            "[marketplaces.kiseki-da]\nsource_type = 'git'\n"
            "source = 'https://github.com/blackrabbit74/kiseki-da.git'\nref = 'v0.1.0-beta.8'\n",
        )
        self.assertEqual(result.marketplace_fingerprint,
                         {"sourceType": "git", "source": "https://github.com/blackrabbit74/kiseki-da.git",
                          "ref": "v0.1.0-beta.8"})

    def test_older_cli_source_remains_supported(self):
        source = {"sourceType": "local", "source": "/source"}
        result = self.inventory([{"name": "kiseki-da", "marketplaceSource": source}])
        self.assertEqual(result.marketplace_fingerprint, source)

    def test_absent_marketplace_does_not_adopt_stale_config(self):
        result = self.inventory([], "[marketplaces.kiseki-da]\nsource_type = 'local'\nsource = '/stale'\n")
        self.assertFalse(result.marketplace)
        self.assertIsNone(result.marketplace_fingerprint)

    def test_missing_or_invalid_config_does_not_guess_source_from_root(self):
        for config in ("", "invalid [", "[marketplaces.kiseki-da]\nsource_type = 'local'\n",
                       "[marketplaces.other]\nsource_type = 'local'\nsource = '/unrelated'\n"):
            with self.subTest(config=config):
                result = self.inventory([{"name": "kiseki-da", "root": "/unverified"}], config)
                self.assertIsNone(result.marketplace_fingerprint)


if __name__ == "__main__":
    unittest.main()
