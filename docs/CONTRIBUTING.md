# Contributing

## Scope

Read [Architecture](ARCHITECTURE.md) and [Validation](VALIDATION.md) before you
change code. Read `AGENTS.md` for the project boundaries, and check
`git status --short` before you edit so you keep unrelated work.

Keep the native title identity and the private data paths stable. Use the
existing source adapters for upstream changes. Read the pinned declaration and a
working example before you add a platform API call.

## Check a change

1. Run `make check` after the edit batch.
2. Build the native title if native code changed.
3. Inspect the generated patches for that build.
4. Run `git diff --check`.
5. Check the source inventory for private files.
6. Record new console results with the environment fields in [Validation](VALIDATION.md#record-a-new-result).
7. Commit and push the reviewed change.

The checks run without a console. A host test never uses a configured console
address. Native build and deployment stay separate operations. A prose edit needs
no rebuild.

## Update a source pin

Choose an explicit upstream commit or release. Download its archive separately.
Record its SHA-256 and the retrieval date in `deps.lock`, and update
[Sources](SOURCES.md). Inspect the diff before you change adapter anchors. Run
the build and the host checks, then test the new artifacts on the console.

Select a fixed revision, never `latest`. Keep dependency archives outside Git.
A checksum identifies the bytes you downloaded. It does not authenticate the
upstream publisher.

## Write documentation

Follow [Writing](WRITING.md). Keep command names, flags, paths, hashes and version
identities exact. Check instructions against the implementation before you
simplify them, and keep the safety conditions and evidence limits. Add a term to
[Glossary](GLOSSARY.md) when a page needs one.

Update the current summaries after new evidence. Keep failures and older artifact
results in the validation history. Change a result only when its own test ran.
