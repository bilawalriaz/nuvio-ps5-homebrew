# Release

## Versioning

`VERSION` holds the release version, for example `0.1.0-alpha.1`. The title
records its own content version in `sce_sys/param.json` as `contentVersion`, for
example `01.000.001`. The build copies that file's identity and content version
into the generated title. Raise the content version in every release so an
installed console sees the update, and so the store catalog can read it from the
tag.

The PS5 Homebrew Store catalog accepts pre-release tags. Use a fixed tag such as
`v0.1.0-alpha.1`, never a moving tag such as `latest` or `nightly`.

## Cut a release

1. Raise `VERSION` and the `contentVersion` in the build template.
2. Run `make check`.
3. Build the candidate with `make build` if native code changed.
4. Test the candidate on the console and record the result in
   [Validation](VALIDATION.md).
5. Commit the source and the documentation.
6. Push the commit.

The release workflow builds on macOS when you push a version tag. It runs the
host checks, builds the native title and helpers, packages the artifacts, and
creates a GitHub release with the assets below.

```sh
git tag v0.1.0-alpha.1
git push origin v0.1.0-alpha.1
```

A documentation change needs no native rebuild. A new native build can carry
different bytes because the build records the build date and time.

## Package locally

Run the package command from a Git checkout:

```sh
make release
```

| Artifact | Contents |
|---|---|
| `PPSA99997.zip` | The `<TITLEID>/` app folder, including `webui/`. This is the store artifact. |
| `nuvio-ps5-<version>.zip` | The complete package: app, `nuvio.elf`, helpers, UI source, receipts. |
| `nuvio.elf` | The single boot payload for Payload Manager. |
| `payloads.json` | A Payload Manager source listing `nuvio.elf` with its hash. |
| `SHA256SUMS` | Hashes for the release assets. |

`PPSA99997.zip` unpacks to a single `PPSA99997/` folder. Users copy that folder to
`/data/homebrew/` and push `nuvio.elf` once per boot. The complete package keeps
the source, the browser UI and the build helpers for a scripted install.

`make release` recreates `release/` and writes `release/ASSETS` with the exact
asset paths. The release workflow uploads those paths, so a stale local file
cannot reach a release.

The package script checks the native file hashes and the helper ELF hashes. It
accepts only the expected helper inventory. The receipt covers the native files
and the helpers. The archive manifest covers the packaged UI and source files.

## Store listing

The [PS5 Homebrew Store catalog](https://github.com/blackbearreloaded/ps5-homebrew-catalog)
lists native PS5 homebrew by title ID. The record lives at `apps/PPSA99997.json`
in that repository and pins one release asset by SHA-256.

The catalog needs:

- A native title with `eboot.bin` and `sce_sys/param.json`, which this project
  builds.
- A public GitHub release with the `PPSA99997.zip` asset attached.
- An icon at a stable HTTPS URL, pinned to a tag. Use `assets/icon.png`.
- The SHA-256 of the release asset.

The daily catalog job follows new releases, so keep the asset name stable and
raise `contentVersion` each time. Submit an update only when the release changes
the listing fields.

## Payload Manager source

`payloads.json` lists each helper with its download URL and SHA-256. Publish it
as a release asset. Users add that URL under Sources in PS5 Payload Manager.

## Distribution rules

1. Record the validation result for the exact candidate.
2. Keep complete corresponding sources for the GPL components you distribute.
   The source directory holds this integration, not every upstream archive.
3. Keep upstream notices and licences with the build.
4. Check the archive for account identifiers, signed URLs and private
   configuration.
5. Keep `/data/nuvio` in any upgrade procedure.

## Announce the release

[Announcement notes](LAUNCH.md) hold a short description, the demonstration plan
and drafts for Hacker News and r/ps5homebrew.
