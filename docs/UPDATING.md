# Update a pinned upstream

This is the repeatable procedure for a new Nuvio or EVO revision. It keeps the
same order every time: report the drift, pin the verified archive, rebuild,
install, then test on the console.

Nothing here contacts the console until step 4. Steps 1 to 3 are host work.

## 1. Report the drift

```sh
make upstream
```

`scripts/update_upstreams.py` reads `deps.lock` and asks each upstream repository
for its newest revision:

| Pin | Upstream | Tracks |
|---|---|---|
| `nuvio-tv-source` | `NuvioMedia/NuvioTVSmart` | newest stable release tag, pinned by commit |
| `evo-player-nuvio-source` | `sainsaji/EVO-PLAYER-PS5` | `main` head |
| `nuvio-official-tv-config` | `NuvioMedia/NuvioTVSmart` | `NuvioTV-Tizen-<tag>.wgt` |
| `ps5-payload-sdk-prebuilt` | `ps5-payload-dev/sdk` | newest stable release |
| `nuvio-pacbrew` | `ps5-payload-dev/pacbrew-repo` | newest stable release |
| `nuvio-klogsrv` | `ps5-payload-dev/klogsrv` | newest stable release |

The report is read-only. A release is never adopted because it is newer: it is
adopted when its archive is downloaded and hashed.

## 2. Pin the new revision

```sh
make upstream            # add --apply through the script for one or more ids
python3 scripts/update_upstreams.py --apply --only nuvio-tv-source
```

For each drifted input the script downloads the archive, records its SHA-256 and
size, sets a version-qualified cache file name, and stamps the retrieval date.
`--apply` then prints the tracked files that still name the previous revision.

Update those files in the same change:

| File | What moves |
|---|---|
| `docs/SOURCES.md` | the pinned identity table |
| `docs/BUILD.md` | the pinned Tizen package version, when it moves |
| `tests/fixtures/*.txt` | the provenance comment, when the fixture is an excerpt of the new revision |
| `scripts/build.py` | the EVO `BUILD_SHA` prefix follows the pin automatically |

Then run the host checks:

```sh
make check
```

`make check` also runs `scripts/docs_check.py`, which fails on a moved document
anchor. A bad anchor is a documentation defect, not a flaky check.

## 3. Rebuild

```sh
make build
```

The builder verifies every archive against `deps.lock` before it extracts it and
stops with `Pinned ... changed` when a source anchor moved. Read that error: it
means the upstream file the adaptation edits is not the file the pin describes.
Correct `scripts/build.py` or `scripts/polish.py` for the new revision, then
rebuild.

The build rewrites `patches/evo.patch` and `patches/nuvio.patch` for review. The
Python adapters already applied those changes. Do not apply the patches again.

A rebuild is not a console result. `firmware_validation` stays `[UNKNOWN]` in the
receipt until step 5.

## 4. Install and launch

Save the receipt of the build that is installed on the console. Without it the
updater cannot verify the files it replaces.

```sh
export PS5_HOST=<console address> PS5_FTP_PORT=<ftp port>
python3 scripts/update.py --previous-receipt <installed receipt>.json
cp build/build.json <installed receipt>.json
python3 scripts/upload.py --file build/permission-watcher.elf   # once per boot
python3 scripts/upload.py --file build/control-3.elf
```

The updater refuses a mounted or running title. Close the app first.

The permission watcher is resident and must be uploaded once per jailbroken boot,
before the title starts.

## 5. Prove it ran

A launch response is not execution. Check both:

```sh
python3 scripts/upload.py --file build/promote.elf   # a running title is matched
```

```sh
# The build string identifies the artifact that actually ran.
head -3 /data/nuvio/evo.log      # over FTP: RETR /data/nuvio/evo.log
```

`control-3` returns a non-negative `launch_result=0x?018` for an accepted launch,
and the low value varies per launch. An accepted launch with no matching process
and no new log line is a failed launch, not a slow one. Record it that way.

Record the result in [Validation](VALIDATION.md) with the firmware, the artifact
hashes, the exact command and the observed behaviour.

## Reverting

The updater keeps each replaced file under `/data/homebrew/ps5-homebrew-dev/` as
`nuvio-<sha256>-<name>`. Copy the previous file back over FTP and relaunch. Keep
the title closed while you do it.
