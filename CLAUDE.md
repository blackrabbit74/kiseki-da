# Kiseki DA repository rules

- Python 3.11+ standard library only. Do not add runtime dependencies or a `pyproject.toml`.
- Runtime source lives under `plugins/kiseki-da/`; public distribution metadata and installer live at repository root.
- Product display name is `Kiseki DA` (Digital Assistant). CLI, plugin, marketplace, and repository slug are `kiseki-da`.
- Run `python3 -m unittest discover -s plugins/kiseki-da/core/tests -t plugins/kiseki-da`, `python3 -m unittest discover -s tests -t .`, and `bash acceptance/smoke.sh` after relevant changes.
- Keep runtime files at or below 60. Count installer, CI, release metadata, and public documentation separately.
- Keep the resident context at or below 2,500 estimated tokens and 9,000 characters; persona alone is at most 220 tokens.
- Persona settings affect expression only. They never alter facts, permissions, approvals, memory, verification, or completion gates.
- Hooks never call an LLM or the network and always fail open. Installer/update/preview may use the network only when explicitly invoked.
- Never publish generated `build/`, caches, local absolute paths, state, session data, or unreviewed third-party quotations.
- Codex plugin manifests follow `.codex-plugin/plugin.json`; do not add unsupported manifest fields. Claude uses its separate manifest and hook definition.
- User-facing text is Japanese. Identifiers, code comments, and commit messages are English.
- Record non-obvious implementation decisions in `docs/DECISIONS.md` with rationale and retirement condition.
