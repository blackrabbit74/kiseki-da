# Kiseki DA acceptance checklist

## Runtime

- [ ] `python3 -m unittest discover -s plugins/kiseki-da/core/tests -t plugins/kiseki-da` passes.
- [ ] `bash acceptance/smoke.sh` prints `ALL PASS` on macOS and Linux.
- [ ] Runtime file count is at most 60; policy is at most 60 lines / 800 estimated tokens.
- [ ] Persona is absent when unset, at most 220 tokens when maximal, and total resident context is at most 2,500 tokens / 9,000 characters.
- [ ] Schema 1 reads without mutation; explicit setup snapshots and writes schema 2.
- [ ] Project A cannot search, load or write Project B state.
- [ ] Persona text cannot change guard, approval, memory or evidence decisions.

## Plugins

- [ ] Both marketplace files and both plugin manifests parse and report version `0.1.0-beta.1`.
- [ ] Claude Code local validation passes and uses exec-form hooks with configured Python.
- [ ] Codex local validation passes and uses default `hooks/hooks.json`.
- [ ] SessionStart, PreToolUse, PostToolUse, Stop and SessionEnd normalize correctly on both hosts.
- [ ] Codex remains `pending activation` until its current hook hash is trusted through `/hooks`.

## Installer

- [ ] `--dry-run` performs no writes, network calls or plugin manager changes.
- [ ] New install, one-host install, both-host install and same-version reinstall are idempotent.
- [ ] Failed install/update/uninstall rolls back; incomplete rollback leaves status 3 and recovery instructions.
- [ ] Update is explicit; normal uninstall preserves `KISEKI_DA_HOME` state.
- [ ] Paths containing spaces and non-ASCII characters work.
- [ ] Optional host hardening is off by default and reversible when selected.

## Blocking publication checks

- [ ] `python3 tools/publication_audit.py` passes on a clean tree.
- [ ] Release ZIP and tar.gz are built only from tracked files and verify against `SHA256SUMS` after extraction.
- [ ] `docs/background/` is absent from the tracked tree and both archives.
- [ ] Windows 11 / WSL2 are marked unsupported; Codex App project scope is marked Local-only.
- [ ] The user has reviewed the final public file list, evidence, tests and hashes before publication.

## Nonblocking beta observation

- [ ] GitHub CI results are reviewed after the repository is available; failures narrow the support claim or trigger a fix.
- [ ] Claude/Codex validators are rerun after host or manifest changes.
- [ ] Persona-on/off quality is observed in real use; any authority-boundary regression stops or disables persona.
- [ ] Windows 11 native, WSL2 and Codex managed Worktree stay unsupported until dedicated canaries pass.
