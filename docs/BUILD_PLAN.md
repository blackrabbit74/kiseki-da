# Build and release plan

## Implementation order

1. Verified source backup and clean public Git repository
2. Schema 2 persona and project-scoped state
3. Dual Claude Code / Codex plugin package
4. Transactional installer, launcher, doctor and rollback
5. Local deterministic tests, privacy audit and release artifacts
6. Human publication gate

## Release gates

- Python 3.11 and 3.14 tests pass on the release build host.
- Claude and Codex plugin manifests pass local validation; host updates continue to be observed during beta.
- All six normalized hooks pass direct and native-host canaries.
- No tracked release file contains a local absolute path, secret, cache or generated build output.
- Persona safety boundaries and 220-token limit pass deterministic tests; live-model quality is observed during beta use.
- Release archive is built only from tracked files and its checksum verifies after extraction.
- Background research is absent from the public tree and archives.
- Publication waits for the user's final review of files, tests and hashes.
