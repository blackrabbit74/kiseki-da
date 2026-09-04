# Publication audit

Status: **BLOCKED until the user approves the exact release candidate.** Platform expansion and live quality observation are nonblocking beta work under `docs/RELEASE-DECISIONS.md`.

## Excluded background material

The pa-harness KILL TEST, decision matrix, architecture history and evidence inventory remain in the verified private handoff backup. They are not tracked or packaged in `v0.1.0-beta.1` because their source, quotation and license audit is incomplete.

## Required before public release

- [ ] Run `python3 tools/publication_audit.py` on a clean tracked tree.
- [ ] Build with `python3 tools/build_release.py`, then run `python3 tools/verify_release_assets.py` to check both hashes and extracted tracked-file inventories.
- [ ] Confirm that `docs/background/` and every other excluded path are absent from tracked files and both archives.
- [ ] Confirm that README and installation docs describe Windows/WSL as unsupported and Codex App as Local-only.
- [ ] Present the final tracked-file list, audit report, tests and release hashes to the user for publication approval.

`python3 tools/build_release.py`が作るものはcandidateだけで、`dist/CANDIDATE_ONLY.txt`を伴います。公開可能なassetを作るには、exampleと同じschemaの外部gate fileへ監査対象のversion・commit SHA・tracked-tree SHA-256と全項目の証拠を記録し、HEADを`v<VERSION>`でtag付けしたうえで`python3 tools/build_release.py --publish-ready --gates <file>`を実行します。いずれかが不一致、または`user_publication_approval`が未完了ならこのcommandは失敗します。

The original Fable build handoff, background research, local generated adapters, session identifiers, private absolute paths and caches are not part of the public tree.
