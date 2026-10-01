# Validation

## Current result

[TESTED-ON-CONSOLE] The owner confirmed QR login, addon sync, focused activation, playback and resumed seeking on the baseline build.
The owner also confirmed native EVO addon browsing and playback.
The first branded build started with Nuvio artwork, but its playback exit failed.
The corrected exit build stopped the decoder and reopened the browser in the console log.
[UNKNOWN] The visible page after that correction still needs owner confirmation.

Host results establish build and regression behavior.
Console logs establish the recorded native actions.
TV observations establish visible behavior.
Keep these results separate.

## Evidence terms

| Label | What the result establishes |
|---|---|
| `[SOURCE-VERIFIED]` | Inspected implementation or a fixed source declaration. |
| `[LOCALLY BUILT]` | Host build, check or mock result. |
| `[TESTED-ON-CONSOLE]` | A recorded console response, console log or owner observation. |
| `[UNKNOWN]` | No sufficient result for this claim. |

Each console result applies to its recorded environment and artifact.
A result for one hash does not certify a later build.
The generated receipt keeps `firmware_validation` as `[UNKNOWN]`.
This document records hardware evidence separately.

## Test environment, 2026-10-01

| Item | Recorded value |
|---|---|
| Console | Retail PS5, CFI-1016A 01Y |
| Firmware | 13.60 |
| Entry chain | Relapse, exact resident revision unknown |
| ELF loader | TCP 9021 observed, exact resident build unknown |
| HEN and mount services | etaHEN, ShadowMount, kstuff and helper revisions unknown |
| SDK | v0.43, archive hash in `deps.lock` |
| Target libraries | pacbrew v0.39, archive hash in `deps.lock` |
| Host | macOS, LLVM/lld 23.1.2, Python 3.13.7, Node 22.23.2 |
| FTP | etaHEN service, TCP 1337 observed |
| Native title | `PPSA99997` |

The original session record remains in the development workspace's `docs/HARDWARE_TEST_LOG.md`.
That workspace is `ps5-homebrew-dev`.
The portable record below omits private addresses and source URLs.
Unknown resident versions remain unknown.

## Artifact history

| Artifact | SHA-256 | Result |
|---|---|---|
| Initial native eboot | `f1f1ddac11d47e7e2ffda7b53d0cd857ce960188342f9c66849f58c4a41eed49` | Browser permission failure, then onboarding after promotion |
| Corrected seek eboot | `8ebe32224ba49a71317578f5817ee6df073b95257cd8ef49f7131508fe742483` | Owner confirmed resumed seeking and native addon comparison |
| First branded eboot | `c4c02603f479325acfa4031c12c7e0dedc31c758de3c3980728260dfb0ff18b5` | Owner confirmed startup branding and reported hidden exit confirmation |
| Corrected exit eboot | `4989d4cabd1f37ade588b2eff66bbb0f1459977ff13aed9e66f93ace4ecd67a8` | Decoder stop and browser reopening logged, visual route result pending |
| Generated runtime | `e6ff45d16adf687855cc3b33b0c8a4132b6504360b221e0a34c7e99fb3ba0036` | Hash checked on console, unchanged through these updates |
| Resident watcher | `8cf4bbe0b889b9063a5775b541027f87a2f5599889e655999a0530eaaec83d89` | Ready message and a later title launch without manual promotion |

The rebuilt watcher differs from the resident watcher.
The rebuilt artifact includes SIGPIPE handling.
It did not replace the resident watcher in this session.
A future upload needs its own hash and boot record.

## Initial network and input failures

Expected: the title opens Nuvio and allows onboarding.
Observed: EVO rendered, then browser error `WV-109145-0` returned to EVO.
The native log showed host preflight success and loopback bind failure with `errno=13`.
The confined promotion helper applied the required credentials and checked them again.
The proxy then listened, and the owner confirmed the Nuvio page.

Expected: X activates the D-pad selection.
Observed: X initially clicked the fixed browser pointer over the QR area.
The input bridge changed activation to the focused Nuvio element.
The owner then confirmed guest continuation, QR login and addon sync.
The official TV package supplied the public login configuration.

Recovery: the owner closed and relaunched the title when requested.
No console firmware, exploit DNS or system file changed.
A reboot was unnecessary.

## Baseline native playback and seeking

Expected: a stream opens, native frames appear, and seeking resumes playback.
One early source returned HTTP 403 before the decoder started.
Another source played successfully.
The original seek guard rejected provider playback with an empty local path.
The controller still entered seeking, and the owner reported a permanent freeze.

The corrected seek build accepted valid provider demuxers.
The owner confirmed that seeking resumed, with some delay compared with other devices.
The log identified native H.264 decoding at 1920×800 and 3840×1600.
One recorded seek settled in 1107 milliseconds.

Filtered excerpt:

```text
PlaybackController: video decoder opened (backend=NATIVE (sceVideodec2), codec=27, 1920x800 @ 23.98 fps)
web: startPlaybackSource -> ok
bc SEEK_AVFRAME rc=0 ts=1980929 strm=0 target=165.243 ms=0
bc SEEK_SETTLE ms=1107 disc=12 pts=165.249 vrel=0.000 arel=0.000 aq=9
EVO vdec native: CLOSE decodes=190 framesout=169 fatal=0
```

The owner closed the title before its update.
The updater checked old files, staged bytes and backups under `/data`.
It imported five private synced addons and the local test addon into native settings.
A separate standalone EVO settings directory was absent.
A fresh title launch returned `launch_result=0x8018` and started the proxy without manual promotion.

Original development commands used exported private addresses:

```sh
python3 apps/nuvio/update.py \
  --previous-receipt /path/to/initial-build.json \
  --sync-addons \
  --test-addon "http://HOST_ADDRESS:4173/ps5-test/manifest.json"
python3 tools/ps5ctl.py upload --file /path/to/control-3.elf
```

These commands ran in `ps5-homebrew-dev`, not this standalone repository.
The standalone equivalents are in [Operations](OPERATIONS.md).

## Branded startup and exit correction

Expected: automatic startup and playback transitions hide EVO menus.
The first branded update replaced eboot, icon, launch images, loading RML and wordmark.
Control-2 reported an installed folder with `mounted:false` before replacement.
The updater checked predecessors, backups and new bytes.
Control-3 reported `running_big_app=-1` and `launch_result=0x4018`.
The console fetched the rebuilt UI assets with HTTP 200.

The owner confirmed Nuvio-branded startup.
Circle then displayed `Opening Nuvio` without stopping playback.
A second Circle returned to video.
[SOURCE-VERIFIED] The loading screen hid the native exit confirmation while playback remained active.

The correction stops Nuvio playback directly on Circle.
It preserves active playback overlays and native settings confirmation.
The owner closed the title before the corrected eboot update.
The updater checked predecessor, backup and replacement hashes.
The corrected launch returned `running_big_app=-1` and `launch_result=0xe018`.

Standalone commands used exported private addresses:

```sh
python3 scripts/update.py \
  --previous-receipt config/installed-polished-build.json
python3 scripts/upload.py --file build/control-3.elf
```

The corrected log identifies build `21524a4a-nuvio_1001-1551`.
It opened a native decoder with codec 173 at 1920×1080.
It settled a seek in 1662 milliseconds.
It closed the decoder with 263 decodes, 253 output frames and no fatal result.
It then reopened the browser successfully.

```text
bc SEEK_SETTLE ms=1662 disc=42 pts=358.733 vrel=0.000 arel=0.000 aq=9
EVO vdec native: CLOSE decodes=263 framesout=253 fatal=0
web: sceWebBrowserDialogOpen -> 0x00000000
```

Recovery backups remain below `/data/homebrew/ps5-homebrew-dev`.
The runtime and artwork stayed unchanged during the exit correction.
No reboot or system write occurred.
[UNKNOWN] The visible restored route still needs owner confirmation.

## Host coverage

[LOCALLY BUILT] Eight host regressions pass for the current code.
They check the HTTP handler, browser focus, provider seek, control responses, saved routes and Circle behavior.
The seek and Circle tests execute patched upstream code with host fixtures.
These tests do not use a console or PS5 SDK.
GitHub CI runs the host checks on Ubuntu.
The native title itself builds through the macOS adapter.

## Acceptance procedure

Use a receipt for the exact installed artifact.
Keep a filtered private log and a record of visible behavior.

1. Start from a fresh jailbreak when testing boot behavior.
2. Upload exactly one watcher for that boot.
3. Launch the title.
4. Check Nuvio branding during startup.
5. Check guest access and focused X activation.
6. Check QR login and addon sync.
7. Play the generated test clip.
8. Check the moving picture and tone.
9. Pause and resume playback.
10. Seek forward and backward several times.
11. Press Circle once.
12. Check the restored Nuvio page and selection.
13. Open Player settings.
14. Check native addon playback and its stop confirmation.
15. Close the title through the app switcher.
16. Relaunch the title.
17. Record any subtitles, formats or session durations tested.

Generated test picture/audio, pause, subtitles and longer stability remain pending.
Fresh-boot behavior with the rebuilt watcher also remains pending.
Complete these checks before public release.

## Record a new console result

Include all fields below:

| Field | Required record |
|---|---|
| Environment | Firmware, console model, exploit, loader, SDK, HEN and mount versions |
| Artifact | Source pins, eboot hash, runtime hash and helper hashes |
| Command | Exact command with private values removed from the public copy |
| Expected result | Visible behavior or response that defines success |
| Observed result | Owner observation and filtered console evidence |
| Recovery | Close, rollback, reboot or other action actually used |
| Limits | Pending tests and unknown version identities |

Preserve failed attempts when adding corrected results.
Keep raw logs, receipts with private state and account data outside Git.
