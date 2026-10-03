# Validation

## What the console tests show

The test console is a retail PS5 on firmware 13.60.

| Check | Result |
|---|---|
| QR login and addon sync | Works. |
| Focused X activation | Works. X activates the selected Nuvio element. |
| Native playback | Works. The log shows `sceVideodec2` decoding H.264 at 1920x800 and 3840x1600. |
| Resumed seeking | Works. Seeking resumes after a short delay. |
| Native EVO addon browsing | Works. |
| Nuvio-branded startup | Works. |
| Playback exit | The log shows the decoder closing and the browser reopening. The restored page itself has no recorded check yet. |

Host checks cover the build and the regression tests. Console logs cover the
recorded native actions. TV observations cover visible behavior. Keep the three
apart.

## Evidence labels

| Label | What the result establishes |
|---|---|
| `[SOURCE-VERIFIED]` | Inspected implementation or a fixed source declaration. |
| `[LOCALLY BUILT]` | Host build, check or mock result. |
| `[TESTED-ON-CONSOLE]` | A recorded console response, console log or TV observation. |
| `[UNKNOWN]` | No sufficient result for this claim. |

Each console result applies to its recorded environment and artifact. A result
for one hash does not certify a later build. The generated receipt keeps
`firmware_validation` as `[UNKNOWN]`.

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

The original session record stays in the private development workspace
`ps5-homebrew-dev`. It holds the private addresses and source URLs. The record
below omits both, and it keeps unknown resident versions as unknown.

## Artifact history

| Artifact | SHA-256 | Result |
|---|---|---|
| Initial native eboot | `f1f1ddac11d47e7e2ffda7b53d0cd857ce960188342f9c66849f58c4a41eed49` | Browser permission failure, then onboarding after promotion |
| Corrected seek eboot | `8ebe32224ba49a71317578f5817ee6df073b95257cd8ef49f7131508fe742483` | Resumed seeking and native addon comparison observed |
| First branded eboot | `c4c02603f479325acfa4031c12c7e0dedc31c758de3c3980728260dfb0ff18b5` | Startup branding observed. Circle left a hidden exit confirmation |
| Corrected exit eboot | `4989d4cabd1f37ade588b2eff66bbb0f1459977ff13aed9e66f93ace4ecd67a8` | Decoder stop and browser reopening in the log |
| Generated runtime | `e6ff45d16adf687855cc3b33b0c8a4132b6504360b221e0a34c7e99fb3ba0036` | Hash checked on the console. Unchanged through these updates |
| Resident watcher | `8cf4bbe0b889b9063a5775b541027f87a2f5599889e655999a0530eaaec83d89` | Ready message, and a later title launch without manual promotion |

The rebuilt watcher adds SIGPIPE handling, so it differs from the resident
watcher. It did not replace the resident watcher in this session. Each new upload
needs its own hash and boot record.

## Initial network and input failures

Expected: the title opens Nuvio and allows onboarding.
Observed: EVO rendered, then browser error `WV-109145-0` returned to EVO. The
native log showed host preflight success and loopback bind failure with
`errno=13`. The permission helper applied the required credentials and read them
back. The proxy listened, and the Nuvio page loaded.

Expected: X activates the D-pad selection.
Observed: X first clicked the fixed browser pointer over the QR area. The input
bridge moved activation to the focused Nuvio element. Guest continuation, QR
login and addon sync then worked. The official TV package supplied the public
login configuration.

Recovery: closed and relaunched the title. No firmware, exploit DNS or system
file changed, and no reboot occurred.

## Baseline native playback and seeking

Expected: a stream opens, native frames appear, and seeking resumes playback.

One source returned HTTP 403 before the decoder started. Another source played.
The original seek guard rejected provider playback with an empty local path, and
the controller still entered seeking, which froze playback.

The corrected seek build accepts valid provider demuxers. Seeking then resumed,
with some delay compared with other devices. The log identified native H.264
decoding at 1920x800 and 3840x1600. One recorded seek settled in 1107
milliseconds.

```text
PlaybackController: video decoder opened (backend=NATIVE (sceVideodec2), codec=27, 1920x800 @ 23.98 fps)
web: startPlaybackSource -> ok
bc SEEK_AVFRAME rc=0 ts=1980929 strm=0 target=165.243 ms=0
bc SEEK_SETTLE ms=1107 disc=12 pts=165.249 vrel=0.000 arel=0.000 aq=9
EVO vdec native: CLOSE decodes=190 framesout=169 fatal=0
```

The updater checked old files, staged bytes and backups under `/data`. It
imported five private synced addons and the local test addon into the native
settings. A fresh title launch returned `launch_result=0x8018` and started the
proxy without manual promotion.

## Branded startup and exit correction

Expected: automatic startup and playback transitions hide the EVO menus.

The first branded update replaced eboot, icon, launch images, loading RML and
wordmark. `control-2` reported an installed folder with `mounted:false` before
the replacement. The updater checked predecessors, backups and new bytes.
`control-3` reported `running_big_app=-1` and `launch_result=0x4018`. The console
fetched the rebuilt UI assets with HTTP 200.

Nuvio-branded startup worked. Circle then displayed `Opening Nuvio` without
stopping playback, and a second Circle returned to video.
[SOURCE-VERIFIED] The loading screen hid the native exit confirmation while
playback stayed active.

The correction stops Nuvio playback directly on Circle. It keeps active playback
overlays and the native settings confirmation. The corrected launch returned
`running_big_app=-1` and `launch_result=0xe018`.

The corrected log identifies build `21524a4a-nuvio_1001-1551`. It opened a native
decoder with codec 173 at 1920x1080, settled a seek in 1662 milliseconds, closed
the decoder with 263 decodes and 253 output frames and no fatal result, then
reopened the browser.

```text
bc SEEK_SETTLE ms=1662 disc=42 pts=358.733 vrel=0.000 arel=0.000 aq=9
EVO vdec native: CLOSE decodes=263 framesout=253 fatal=0
web: sceWebBrowserDialogOpen -> 0x00000000
```

Recovery backups stay below `/data/homebrew/ps5-homebrew-dev`. The runtime and the
artwork did not change during the exit correction. No reboot or system write
occurred.

## Nuvio 1.2.2 update, 2026-10-03

[TESTED-ON-CONSOLE] The pinned Nuvio source moved from 1.2.1 to 1.2.2
(`358d08cf`), and the official TV configuration moved to the 1.2.2 package.
The EVO pin did not move: `main` at `21524a4a` is still the newest revision, and
the newest EVO release asset is older than that commit. The rebuild changed only
`eboot.bin` in the title inventory. The runtime, artwork and loading RML stayed
byte-identical.

[TESTED-ON-CONSOLE] The updater accepted the installed predecessor and replaced
only `eboot.bin`, with `control-2` reporting an installed, unmounted folder.
Six launches of the new eboot returned an accepted `launch_result`
(`0x18` to `0xa018`, low value varying per launch). **The title never started**:
`promote.elf` matched no running `PPSA99997` process on every probe, and
`/data/nuvio/evo.log` gained no byte. Restoring the previous eboot
`4989d4ca` and launching again made the process visible to `promote.elf` and
resumed the log at build `21524a4a-nuvio_1001-1551`.

An accepted launch response is therefore not execution, exactly as the working
notes warn. The new eboot is [UNKNOWN] until it is retested with the app closed.
The cause is not established. The console was left on the previous eboot.

The host toolchain reproduces the previous build only in behaviour, not in bytes:
two builds from the same sources differ in the signed container.

[TESTED-ON-CONSOLE] The owner reported the whole app failing to load any catalog
entry or thumbnail during this session. The cause was the console's DNS
connectivity, not this change. The app recovered when connectivity did.

[LOCALLY BUILT] The owner reported a white flash between the native splash screen
and the Nuvio interface when a stream exits, visible in a dark room. The PS5
browser paints its own document background before the Nuvio CSS applies. The
served `index.html` now carries
`<style>html,body{background-color:#000;margin:0}</style>` as the first element
of `<head>`, so the first paint is black. `scripts/build.py` applies it through
`patch_index()`, covered by two host tests. A headless browser confirmed the
page background stays dark with the style first in the document. Owner
confirmation of the stream-exit transition is pending.

## Host coverage

[LOCALLY BUILT] Eight host regressions pass. They cover the HTTP handler, browser
focus, provider seek, control responses, saved routes and Circle behavior. The
seek and Circle tests run the patched upstream code against host fixtures. These
tests use no console and no PS5 SDK. GitHub CI runs the host checks on Ubuntu.
The native title builds through the macOS adapter.

## Acceptance procedure

Use a receipt for the exact installed artifact. Keep a filtered private log and a
record of the visible behavior.

1. Start from a fresh jailbreak when you test boot behavior.
2. Push exactly one watcher for that boot.
3. Launch the title.
4. Check Nuvio branding during startup.
5. Check guest access and focused X activation.
6. Check QR login and addon sync.
7. Play the generated test clip.
8. Check the moving picture and the tone.
9. Pause and resume playback.
10. Seek forward and backward several times.
11. Press Circle once.
12. Check the restored Nuvio page and selection.
13. Open Player settings.
14. Check native addon playback and its stop confirmation.
15. Close the title through the app switcher.
16. Relaunch the title.
17. Record the subtitles, formats and session durations you tested.

Generated test picture and audio, pause, subtitles and longer stability are still
open. Fresh-boot behavior with the rebuilt watcher is also open.

## Record a new result

Include every field below.

| Field | Required record |
|---|---|
| Environment | Firmware, console model, exploit, loader, SDK, HEN and mount versions |
| Artifact | Source pins, eboot hash, runtime hash and helper hashes |
| Command | Exact command with private values removed from the public copy |
| Expected result | Visible behavior or response that defines success |
| Observed result | What the TV showed and the filtered console evidence |
| Recovery | Close, rollback, reboot or other action actually used |
| Limits | Open tests and unknown version identities |

Keep failed attempts when you add a corrected result. Keep raw logs and receipts
with private state outside Git.
