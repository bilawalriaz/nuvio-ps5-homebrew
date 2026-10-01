# Contributing

## Change scope

Read [Architecture](ARCHITECTURE.md) and [Validation](VALIDATION.md) before code changes.
Read `AGENTS.md` for project boundaries.
Check `git status --short` before editing.
Preserve unrelated work.

Keep the native title identity and private data paths stable.
Use the existing source adapters for upstream changes.
Read the pinned declaration and an example before adding a platform API call.
Do not infer firmware support from an SDK header or successful link.

## Check a change

1. Run `make check` after the edit batch.
2. Build the native title if native code changed.
3. Inspect generated patches for that build.
4. Inspect `git diff --check`.
5. Inspect the final source inventory for private files.
6. Record new console results with the required environment fields.
7. Commit and push the reviewed change.

The checks run without a console.
A host test must not use a configured console address.
Native build and deployment remain separate operations.
Do not rebuild only to validate a prose edit.

## Update a source pin

Choose an explicit upstream commit or release.
Download its archive separately.
Record its SHA-256 and retrieval date in `deps.lock`.
Update [Sources](SOURCES.md) with the source identity.
Inspect the diff before changing adapter anchors.
Run the build and host checks.
Test the new exact artifacts on the console.

Do not silently select `latest`.
Keep dependency archives outside Git.
Checksums identify downloaded bytes but do not authenticate the upstream publisher.

## Write documentation

Follow [Writing](WRITING.md).
Keep command names, flags, paths, hashes and version identities exact.
Check instructions against the implementation before simplifying them.
Keep safety conditions and evidence limits when shortening a sentence.
Define a technical term in [Glossary](GLOSSARY.md) when needed.

Update current summaries after new evidence.
Keep failures and older artifact results in the validation history.
Do not change a pending test into a success without its result.
