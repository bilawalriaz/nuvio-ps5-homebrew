# Release

## Current release state

The current version is `0.1.0-alpha.1`.
The source repository is public.
No binary prerelease is published.
The owner requested public-project preparation on 2026-10-01.
The owner authorized this separate public source repository.
Binary publication remains a separate action.
See [Launch](LAUNCH.md) for the source announcement and binary gates.
The visible route after the corrected playback exit remains pending.
See [Validation](VALIDATION.md) before changing that status.

## Prepare the candidate

1. Save the currently installed receipt privately.
2. Run `make check`.
3. Build the candidate if native code changed.
4. Inspect the generated patches.
5. Check the candidate receipt and source pins.
6. Test the exact candidate on the console.
7. Record the result in `docs/VALIDATION.md`.
8. Commit the source and documentation changes.
9. Push the reviewed commit to this source repository.

A documentation change does not require a native rebuild.
A new native build can have a different hash because the build includes time-dependent metadata.
Pinned inputs alone do not establish byte-for-byte reproducibility.

## Package the candidate

Run the package command from a Git checkout:

```sh
make release
```

The output is:

```text
release/nuvio-ps5-0.1.0-alpha.1.zip
release/SHA256SUMS
```

The package script checks native file hashes and helper ELF hashes.
It accepts only the expected helper inventory.
It includes UI files with permitted extensions.
It also includes tracked and unignored source files from the checkout.
Run `make check` before packaging to check that source inventory.

| Archive path | Contents |
|---|---|
| `app/PPSA99997/` | Generated native folder title |
| `ui/` | Built browser UI |
| `helpers/` | Fixed-purpose ELF helpers |
| `source/` | Integration source, patches and documentation |
| `build.json` | Native, helper and input hashes |
| `MANIFEST.sha256` | Hashes for packaged files |

The packaging script does not download account state from the console.
It does not include ignored cache, configuration, log or build source directories.
The receipt covers native files and helpers.
The archive manifest also covers the packaged UI and source files.

The archive layout differs from a source build directory.
The install scripts expect the source builder's output layout.
They do not consume the archive directly.
Use the documented source build procedure for scripted installation.
The archive supplies folder-title artifacts for a deliberate manual deployment.
It does not provide a retail package or one-click installer.

## Public release policy

This public source repository has no binary release.
Local packages remain development artifacts until acceptance and source review are complete.
Do not upload local archives as part of a source update.

Before creating a public binary prerelease:

1. Complete the binary distribution checks below.
2. Record the exact candidate's validation results.
3. Include complete corresponding sources and required notices.
4. Create release notes identifying the candidate hash and remaining limitations.
5. Publish only after the owner's binary-release instruction.

## Before public binary distribution

Complete the pending console acceptance checks.
Record exact versions when available.
Keep unknown versions explicit.
Review all target library licenses and notices.
Provide complete corresponding sources for distributed GPL components.
Include the required source revisions, modifications and build instructions.
The current source directory contains the integration, not every upstream source archive.

Check the archive for account identifiers, signed URLs and owner configuration.
Retain public browser configuration only from the pinned official Nuvio package.
Confirm the repository visibility and release action with the owner's publication instruction.
Preserve `/data/nuvio` in any upgrade procedure.
