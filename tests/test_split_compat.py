"""Names that moved out of core/ctx/cli.py and core/ctx/store.py stay importable from the old place.

The split of 2026-10-19 (docs/DECISIONS.md) keeps `from core.ctx.cli import X` and `from core.ctx.store import X`
working for the installer, tests and customer code until 0.2.0. Each name must resolve to the very object
defined in its new module. tomlemit.emit_toml is left out: store.emit_toml is its profile wrapper.
"""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
import unittest


PLUGIN = Path(__file__).resolve().parents[1] / "plugins" / "kiseki-da"
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))
# Import at collection time: other installer tests later put a temporary runtime copy on sys.path.
from core.ctx import cli, store, tomlemit  # noqa: E402

OLD_HOME = {"cli_common": "cli", "cmd_task": "cli", "cmd_memory": "cli", "cmd_persona": "cli", "cmd_admin": "cli",
            "fileio": "store", "tomlemit": "store", "schemacheck": "store"}
MOVED = {
    "cli_common": (
        "_err", "_out", "_emit_json", "_json", "_make_store", "_common_store", "_confirm_text",
    ),
    "cmd_task": (
        "REASON_JA", "cmd_task_override", "_card_summary", "_card_dict", "_split_criterion",
        "_split_evidence", "cmd_task_new", "cmd_task_show", "cmd_task_list", "cmd_task_set",
        "cmd_task_close", "cmd_task_defer", "cmd_task_brief", "cmd_verify_run",
    ),
    "cmd_memory": (
        "SEARCH_KINDS", "cmd_context", "_parse_since", "_parse_kinds", "cmd_search", "cmd_capture",
        "cmd_candidate_add", "_age_days", "cmd_candidate_list", "cmd_approve", "cmd_reject",
        "cmd_remember",
    ),
    "cmd_persona": (
        "_PERSONA_OPTION_FIELDS", "_PREVIEW_PROMPT", "_read_json_object", "_validate_identity",
        "_ask", "_ask_choice", "_collect_persona", "_preview_hosts", "_fixed_preview",
        "_live_preview", "_print_preview", "_save_identity", "cmd_setup", "cmd_persona_show",
        "_persona_args", "cmd_persona_edit", "cmd_persona_preview", "cmd_persona_reset",
    ),
    "cmd_admin": (
        "cmd_policy", "cmd_init", "cmd_build", "_check_log_event", "cmd_log", "cmd_report",
        "cmd_project_add", "cmd_project_list", "cmd_project_remove", "_session_store",
        "cmd_session_list", "cmd_session_clear", "cmd_evals_run",
    ),
    "fileio": (
        "dumps", "_atomic_write", "_append_jsonl", "_lock", "_unlock", "_locked_append",
        "_iter_jsonl",
    ),
    "tomlemit": (
        "_BARE_KEY", "_toml_key", "_toml_str", "_toml_value",
    ),
    "schemacheck": (
        "_SCHEMA_FILES", "_schema_type", "_schema_table", "_schema_tables", "_check_obj", "_is_type",
    ),
}

MODULES = {name: importlib.import_module(f"core.ctx.{name}") for name in MOVED}


class SplitCompatTest(unittest.TestCase):
    def test_moved_names_resolve_from_the_old_module(self):
        for new, names in MOVED.items():
            old = {"cli": cli, "store": store}[OLD_HOME[new]]
            mod = MODULES[new]
            for name in names:
                with self.subTest(module=new, name=name):
                    self.assertIs(getattr(old, name), getattr(mod, name))

    def test_cli_does_not_leak_what_command_modules_import(self):
        for name in ("shutil", "tempfile", "hashlib", "shlex"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(cli, name))

    def test_store_emit_toml_omits_empty_sections_only(self):
        data = {"a": [], "constraints": [], "b": 1}
        self.assertEqual(store.emit_toml(data), "a = []\nb = 1\n")
        self.assertEqual(tomlemit.emit_toml(data), "a = []\nconstraints = []\nb = 1\n")


if __name__ == "__main__":
    unittest.main()
