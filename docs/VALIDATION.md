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
| Console UI payload `nuvio.elf` | `b0b41a6f8d8882c2f9d0a61199bbdddfadcd41ea1691f1d2fe8a9740d4702e3d` | Served the whole browser UI from the console with no LAN host |
| Console UI payload `nuvio.elf` with settle | `67bc0d9986bb0abb9b6c719c217fab01470af4f53300cb3fac2cee8c6eb50f44` | Title bound its proxy and loaded the interface from the console |
| Loopback diagnostic eboot (final host build) | `0e4fc05f5f7b42902d65fd9679110745fd7c1e52b10c3d208df9ce96729196da` | Build ID `21524a4a-nuvio-dirty_1007-2338`. Not installed |
| Loopback diagnostic eboot (installed for gate test) | `78d091ee7a352b525bbe1d08a199d64969b4a7aa5a107ca39f9615ab03d13b07` | Build ID `21524a4a-nuvio-dirty_1008-1241`. On-console hash verified. Launch pending |

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

## Unpromoted loopback diagnostic

[SOURCE-VERIFIED] The proxy startup now reports `socket`, `bind`, `listen` and
browser connection results as separate log events. `make build` produces the
diagnostic title from the pinned EVO source. It does not load `nuvio.elf` or
`promote.elf` and does not change the title's credentials.

[UNKNOWN] The unpromoted title's loopback bind and browser connection results
remain pending a console run on firmware 13.60. Keep the existing boot helper
and installation flow until this gate passes.

[LOCALLY BUILT] The diagnostic title built from EVO
`21524a4a6effa65312be2026042e44a96efca4c6`. The final `make build` on
2026-10-08 produced `eboot.bin` SHA-256
`0e4fc05f5f7b42902d65fd9679110745fd7c1e52b10c3d208df9ce96729196da` and build ID
`21524a4a-nuvio-dirty_1007-2338`. The signed container inspector reported
authority `0x3100000000000002`, program type `1` and valid integrity. This is
build evidence only. An earlier diagnostic build (`8626ee00…`, build ID
`21524a4a-nuvio-dirty_1007-2327`) went through the blocked transfer attempt.
The updater did not install it.

[TESTED-ON-CONSOLE] On 2026-10-08, the loader and FTP services answered. A
fixed-purpose `control-2.elf` call reported `PPSA99997` installed as an unmounted
folder with fake signing enabled. The diagnostic eboot was not installed. The
update stopped at staged-file verification because SDK `ftpsrv` transforms PS5
containers when FTP `RETR` reads them. The readback is not the file stored on the
console. I removed the staged file. The updater did not rename it over the title
eboot, so the installed title eboot stayed in place.
This matches the FTP readback behavior recorded in private KI-047. The bind gate
is still [UNKNOWN].

[TESTED-ON-CONSOLE] A follow-up used `control-5.elf` to hash the installed and
staged eboots on the console and make a raw rollback copy. It verified and
installed eboot `78d091ee7a352b525bbe1d08a199d64969b4a7aa5a107ca39f9615ab03d13b07`.
`control-2` reported the title still unmounted. The updated eboot has not launched
yet, so socket permission results remain pending.

[TESTED-ON-CONSOLE] On 2026-10-09, the loader (9021) and FTP service (2121)
answered at the owner-supplied address. `control-2.elf` reported the title
installed, fake signing effective and unmounted. `control-3.elf` could not start
it: `running_big_app=8216` and `launch refused: close the running title or sign
in first`. The installed diagnostic eboot did not launch in this attempt. It
produced no socket, bind, listen or browser-connection result. The log read
afterward contained prior build records, so it does not count as evidence for
this attempt. The permission gate remains [UNKNOWN].

### Corrected diagnostic and signing comparison, 2026-10-09

[SOURCE-VERIFIED] The earlier preflight bypass used a C macro that the builder
never enabled. The title could stop before its listener test when the UI helper
was absent. The adapter now inserts the bypass only in diagnostic sources,
without an additional compiler guard.

[LOCALLY BUILT] The corrected native ELF contains the diagnostic bypass message.
Two signed containers use the same compiled module, build ID
`21524a4a-nuvio-dirty_1009-1342`:

| Profile | Eboot SHA-256 | Authority |
|---|---|---|
| Default | `bb55d04d829c15aa149f992ae5e9d38fa6e724c61dc3188a769b1824a5bedb6f` | `0x3100000000000002` |
| SDK install-app example | `4ecb5c7fc811cdaccf5cdb8d51cfd274bf9218594594d96c75de2ac582944da4` | `0x3800000000000022` |

Both pass the container integrity inspection.
The SDK profile embeds the exact 136-byte authentication record from the pinned
SDK example, with its first eight bytes replaced by the example's authority.
Its source file SHA-256 is
`a28a0b34ef75824a9d74ca5895fbeda7256808bf6d2060336cfa35dd9359c3b4`.
The generated runtime remains
`e6ff45d16adf687855cc3b33b0c8a4132b6504360b221e0a34c7e99fb3ba0036`.

[LOCALLY BUILT] All 35 host tests, documentation checks and source checks passed.
Feedback tests reject old logs, helper mismatches and installed-artifact mismatches.
The release packager rejects diagnostic builds and permission-test signing profiles.

[UNKNOWN] Neither corrected container has a console result yet.
The owner confirmed this boot's jailbreak, closed apps and no Nuvio helper.
The configured console address was unreachable from the host.

Install the corrected default profile first and run the loopback feedback check.
If it fails to bind, close the title and install the SDK profile.
Keep the helper unloaded for both tests.
Use each installed receipt with the updater and preserve its raw rollback copy.
Record fresh listener events separately from UI or playback results.

### Console sequence

1. Run `make check` on the macOS build host.
2. Build with `NUVIO_WORK_DIR=/tmp/nuvio-ps5-hash-build2 make build`.
3. Record the `eboot.bin` SHA-256 from
   `/tmp/nuvio-ps5-hash-build2/build.json`.
4. Jailbreak the PS5 for this boot. Start the normal ELF loader, FTP service and
   ShadowMount.
5. Close Nuvio through the app switcher.
6. Run the updater. It uses `control-5.elf` to hash the installed eboot, save a
   raw on-console backup and verify the staged eboot. Do not upload `nuvio.elf`
   or `promote.elf` for this gate test.

```sh
export PS5_HOST="<console-address>" PS5_FTP_PORT="<ftp-port>"
export PS5_READ_IDLE_TIMEOUT=60
export NUVIO_WORK_DIR="/tmp/nuvio-ps5-hash-build2"
python3 scripts/update.py --previous-receipt "/path/to/installed-build.json"
```

7. Close any foreground big app and return to the dashboard. Keep
   `nuvio.elf` and `promote.elf` unloaded. Launch Nuvio from its home-screen
   tile.
8. Read `/data/nuvio/evo.log` over FTP and record these events separately:
   `server: socket`, `server: bind`, `server: listen`, and
   `server: connection accepted`.
9. Run `control-5.elf` again. Compare its on-console installed hash and the
   logged build ID with the candidate receipt. Record the console model, resident
   support-stack versions, exact command, output and recovery in the private
   hardware log.

The `connection accepted` event excludes the proxy's internal shutdown wake-up.
If bind succeeds, the browser must produce an accepted connection before this
gate passes. A load error for the missing UI server does not change the socket
results.

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

[TESTED-ON-CONSOLE] The first rebuild did not start. Six launches returned an
accepted `launch_result` (`0x18` to `0xa018`, low value varying per launch)
while `promote.elf` matched no running `PPSA99997` process and
`/data/nuvio/evo.log` gained no byte. Restoring the previous eboot `4989d4ca`
and launching again made the process visible to `promote.elf` and resumed the log.

[SOURCE-VERIFIED] The cause was the link, not the sources. The packaging step
expands `${PS5_SYSROOT}/lib` with a shell glob, and with `--as-needed` the first
stub that satisfies a kernel symbol is the one recorded in the module's import
table. Under the ambient UTF-8 collation `libkernel_web.so` sorted before
`libkernel.so`, so the module imported `libkernel_web.prx`, the browser-safe stub.
The working build imports `libkernel.prx`. `scripts/build.py` now pins `LC_ALL=C`
and [Build](BUILD.md) explains why.

[TESTED-ON-CONSOLE] With that fix the rebuilt title starts and runs. The log
records `BUILD 21524a4a-nuvio-dirty_1003-1441`, the proxy hook injected into `/`,
660718 bytes of browser storage restored and the route `home`. An accepted launch
response is still not execution: check `promote.elf` and the log build string
every time.

[TESTED-ON-CONSOLE] A launch sometimes needs several attempts before the title
stays up. One attempt in this session failed the same way. Treat a single failed
launch as inconclusive and retry before you record a failure.

[TESTED-ON-CONSOLE] During this session, catalogue entries and thumbnails failed
to load across the app. The console's DNS connectivity caused it, not this
change. The app recovered when connectivity did.

[LOCALLY BUILT] A white flash appears between the native splash screen and the
Nuvio interface when a stream exits, visible in a dark room. The served
`index.html` carries
`<style>html,body{background-color:#000;margin:0}</style>` as its first head
element, applied through `patch_index()` and covered by host tests.

The port tried a `media="print"` stylesheet that switched to `all` on load, to
stop the 544 KB `css/bundle.css` holding back the first paint. The console's
browser then rendered Nuvio unstyled, so the pattern is not usable here and the
build keeps the plain render-blocking `<link>`. The visible transition still
needs a console check.

[TESTED-ON-CONSOLE] The build now installs the repository artwork in
`assets/icon.png` (512x512) as the title icon. The console copy verified
byte-for-byte at `90ed6493`, and the previous icon (1fe88349) stays under
`/data/homebrew/ps5-homebrew-dev`. The PS5 caches a title icon. A second
registration reported `changed:false` and left the icon URL stamp at
`v=1790864733-28006`, so the home-screen tile keeps the old artwork until the
console recreates the title record.

## Console serves its own UI, 2026-10-03

[TESTED-ON-CONSOLE] The browser UI now travels inside the title folder and the
boot payload serves it, so no computer runs while you use the app.

- Artifact: `nuvio.elf`
  `b0b41a6f8d8882c2f9d0a61199bbdddfadcd41ea1691f1d2fe8a9740d4702e3d`.
- Folder: the build's `webui/` (117 files, 17 MB) copied into
  `/data/homebrew/PPSA99997/` and verified byte-for-byte over FTP.
- Configuration: `/data/nuvio/nuvio.conf` with `host=127.0.0.1`, `port=4173`,
  `https=0`.
- Command: push `nuvio.elf` to loader 9021, then launch `PPSA99997`.
- Expected: the title opens its own interface and no LAN host answers.
- Observed: with the host UI server stopped, the payload printed
  `NUVIO ui: serving /data/homebrew/PPSA99997/webui on 127.0.0.1:4173` and the
  console fetched 68 UI requests (`/`, `/index.html`, `/css/bundle.css`,
  `/app.bundle.js`, `/res/i18n/en.json`, `/assets/libs/hls.min.js`). The native log
  records `proxy: injected hook into / (2568 bytes)` and `page: route authQrSignIn`.
- Recovery: the console keeps the previous origin at
  `/data/nuvio/nuvio.conf.before-console-ui`.

[TESTED-ON-CONSOLE] The session measured two approaches and rejected one. A
payload listener bound to the console's own LAN address is reachable from another
machine, but the title's proxy did not load the page from that address
(`page watchdog: ... did not load`), so the working origin is loopback. A threaded
accept loop inside the payload bound the port and then stopped answering. The
payload now drives one single-threaded accept loop from its own thread of control.

The visible transition still needs a console check. The session found the
credential timing that blocked the launch later the same day, in
[Console UI working end to end](#console-ui-working-end-to-end-2026-10-03).

## Console UI working end to end, 2026-10-03

[TESTED-ON-CONSOLE] After a fresh install of the title from this build, the app
launched, bound its proxy and loaded the interface from the console with no
computer running.

- Install: all 223 files of `output/app/PPSA99997/` written to
  `/data/homebrew/PPSA99997` (68,133,019 bytes). The installed tree matches
  `build.json` exactly.
- Module: `eboot.bin` 38,847,060 B sha256 `f7ea5526…` and `sce_module/libc.prx`
  1,284,674 B sha256 `e6ff45d1…`, both read on the console with a payload.
- Payload: `nuvio.elf` sha256 `67bc0d99…`.
- Observed: `web: server: 127.0.0.1:8686 ready, proxying http://127.0.0.1:4173`,
  `web: proxy: injected hook into / (2568 bytes)`, `web: storage: restored 717849
  bytes`, `web: page: route home`, and 104 requests in `/data/nuvio/ui.log`.

[TESTED-ON-CONSOLE] Two faults had to be fixed first.

The payload scans for the title process and grants it the credentials its
loopback bind needs. Writing those credentials while the title's PRX modules
still resolve faults the process. The session measured three timings on one boot:

| Credential write | Result |
|---|---|
| immediately on detection (~0.25 s) | `PRX_PROCESS_STARTUP_FAILURE` or `PRX_NOT_RESOLVED_FUNCTION` |
| delayed 2500 ms | app runs, `bind/listen 127.0.0.1:8686 failed errno=13`, `WV-109145-0` |
| delayed 500 ms | app runs and binds, interface loads |

The payload now waits 500 ms (`NUVIO_PROMOTE_DELAY_MS`). The scan also stopped
calling `sceKernelGetAppInfo` for every process each cycle, a call kstuff patches
(`[kstuff.elf] … sceKernelGetAppInfo: Broken pipe`). This timing is the likely
explanation for the older "a launch can take several attempts" note.

[TESTED-ON-CONSOLE] A raw-ELF `eboot.bin` cannot start. The system rejects it
before the app runs: `sceSblAuthMgrAuthHeader returned unexpected error 46` and
`sceSblACMgrGetFsSandboxType(.../eboot.bin) failed. 0x80020008`. Deploy the
converted `output/app/PPSA99997/eboot.bin`, never the `.build/eboot.elf`.

## Host coverage

### Hash-helper deadline, 2026-10-09

[SOURCE-VERIFIED] The installer previously killed helper subprocesses after
40 seconds, while the eboot hash helper allowed 60 seconds between reads.
The parent now covers connection, transfer and response budgets.
It also follows a longer configured response timeout.

[LOCALLY BUILT] `make check` passed all 25 tests, documentation checks and
private-artifact checks. The regression checks default and extended hash-helper
deadlines. This change needs no native rebuild.

[LOCALLY BUILT] Eight host regressions pass. They cover the HTTP handler, browser
focus, provider seek, control responses, saved routes and Circle behavior. The
seek and Circle tests run the patched upstream code against host fixtures. These
tests use no console and no PS5 SDK. GitHub CI runs the host checks on Ubuntu.
The native title builds through the macOS adapter.

## Acceptance procedure

Use a receipt for the exact installed artifact. Keep a filtered private log and a
record of the visible behavior.

1. Start from a fresh jailbreak when you test boot behavior.
2. Push exactly one payload, `nuvio.elf`, for that boot.
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
open. Fresh-boot behavior with the console UI payload is also open, and the
visible playback-return transition still needs a console check.

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

## Title-local UI experiment, 2026-10-09

[LOCALLY BUILT] Native build command:

```sh
NUVIO_WORK_DIR=/tmp/nuvio-ps5-title-ui-20261009 python3 scripts/build.py --auth-profile sdk-install-app --title-ui
```

Build `21524a4a-nuvio-dirty_1009-1353` has eboot SHA-256
`5298741976bf73ffa25b41420527967c23845b7484973c6a15768847fbaa5009`,
runtime SHA-256
`e6ff45d16adf687855cc3b33b0c8a4132b6504360b221e0a34c7e99fb3ba0036`,
`ui_hosting: title`, `auth_profile: sdk-install-app` and no diagnostic mode.
Container integrity passed. It uses the same runtime as the two corrected
permission diagnostics. The console still has the previous diagnostic.

Seven host tests passed with AddressSanitizer and UndefinedBehaviorSanitizer.
They exercise the actual C responder over sockets: HTML bridge insertion, HEAD,
large streamed assets, traversal and symlink rejection, missing files, oversized
HTML and a disconnected browser. These are host results.

[UNKNOWN] Firmware startup and packaged-file access remain open. After comparing
the two permission diagnostics, install this title-local build, run the feedback
command with its receipt and observe the UI without either Nuvio helper loaded.
The UI gate requires fresh bind/listen/connection, packaged asset status 200 and
a Nuvio route. Then test generated video, sound, pause, seek, Circle return and
relaunch. Record the full environment tuple in the private hardware log.

## Corrected signing comparison, 2026-10-09

[TESTED-ON-CONSOLE] On firmware 13.60, with a current jailbreak and neither
Nuvio helper loaded, the corrected default-profile diagnostic launched and
reported `server: socket ok fd=25` followed by
`server: bind failed port=8686 errno=13`. Raw staging and installed hashes matched
`bb55d04d829c15aa149f992ae5e9d38fa6e724c61dc3188a769b1824a5bedb6f`.

The SDK-example profile of the same compiled module installed with raw hash
`4ecb5c7fc811cdaccf5cdb8d51cfd274bf9218594594d96c75de2ac582944da4`.
Two accepted launches produced no fresh BUILD or socket events within the
30-second observation windows. The status response reported an unmounted title between attempts.
[UNKNOWN] Its bind behavior remains unknown. The metadata needs a launch
investigation before adoption. The title-local UI variant has no console result.

The private hardware log records the full environment tuple, commands and
backup evidence. No UI assets, runtime, settings or accounts changed during
this eboot-only comparison.

[TESTED-ON-CONSOLE] Follow-up owner observation: the SDK-profile title shows PRX
startup error `0xa0020101` and does not open. Restored the default diagnostic
with raw staged and installed hash verification. The default profile's measured
unpromoted bind failure remains unresolved. The private hardware log records
the restoration command and evidence.

## Default authority with SDK info and automatic closure, 2026-10-09

[TESTED-ON-CONSOLE] Retained default authority `0x3100000000000002` and signed
the same diagnostic module with the remaining SDK example auth info. Candidate
eboot sha256: `8ca26000911fdb4534eaa376c669d3da54ae39a338305902bedc856e7749a897`.
Raw staging and installed hashes matched, but an accepted launch produced no
fresh BUILD/socket events within 30 seconds. No bind result established.

Restored the default diagnostic, then observed its fresh BUILD, socket success
and bind failure errno=13. The new fixed-title close helper then returned process
evidence, and the close command verified the title unmounted. Close helper sha256:
`6cf9959af530d9b23bfc25fbe2cb68f0c7481eba2526ca8ad61effceb99a6053`.
The private hardware log records commands, tuple, rollback and filtered logs.

[UNKNOWN] Network permissions inside the title remain unresolved. Both SDK
auth-info variants remain experiments.

## Embedded promotion and page crash, 2026-10-09

[TESTED-ON-CONSOLE] Firmware 13.60, SDK v0.43, existing loader TCP 9021,
FTP v0.21.1 TCP 2121. Exploit, loader and HEN revisions remain unknown.
No Nuvio helper was manually loaded before the comparison.
Updates used `scripts/update.py --previous-receipt` with preserved eboot-only
receipts. Feedback used `scripts/feedback.py --gate ui`.

Descriptor-mode changes failed before connection: fcntl returned errno13,
and ioctl(FIONBIO) returned errno13. Socket creation with SOCK_NONBLOCK worked.
Eboot SHA-256: `dc0fbf4f35cd90795f60fc98ad080da1c7fbe21b404dedfc43aad83b76c15a9f`.
Embedded promotion ELF SHA-256:
`502ae8189cda8dbe0b82c6dc2b11a1c932dba6f4773e455e5ac532bb999eb952`.
Fresh BUILD `21524a4a-nuvio-dirty_1009-1456` recorded promotion verification,
bind/listen success and browser connection accepted. Feedback verified no page response or route. The owner saw Opening Nuvio, a white screen, then a crash.

The kernel log reported SIGSYS in eboot.bin. The matching app return address
maps to conn_thread immediately after nuvio_local_ui_send.
[INFERENCE] openat in the responder is the likely unsupported syscall.
The next comparison uses ordinary open with O_NOFOLLOW on each path component.
Updates keep the title closed while replacing its files.
The private environment hardware log holds exact commands, hashes, logs and recovery.
Full page, playback, repeated launch and fresh-boot checks remain pending.

## Ordinary file opens reach the home route twice, 2026-10-09

[TESTED-ON-CONSOLE] Same boot and environment as the preceding experiment.
Eboot SHA-256: `56f7b86cf867e0c36a031f392dca7ecd05383313a7791cb836f30625c0552e6a`.
Embedded promotion ELF SHA-256:
`a505a32a369488fc4ae35df6c3b98d9a862af070f407309a11d89c4b719b5934`.
The updater verified raw staged and installed bytes before replacement.

The responder uses ordinary open/O_NOFOLLOW on each path component.
Two `scripts/feedback.py --gate ui` runs automatically closed and relaunched the title.
Both verified embedded promotion, bind/listen, packaged HTTP200 responses,
`page: route home` and `Feedback: ui_route_observed`.
No Nuvio helper was manually uploaded. The private hardware log records commands
and recovery. Existing runtime, UI assets and settings remain installed.
Playback, a full asset update and a fresh-jailbreak launch remain pending.

[TESTED-ON-CONSOLE] Owner confirmed playback, seeking and Circle return all work
on the ordinary-open build. This observation uses the existing installed UI assets.

## Complete file update, 2026-10-09

[TESTED-ON-CONSOLE] Reconciled the installed artwork and 117 browser assets
against read-only FTP hashes. The first attempt refused an asset missing from
the old receipt. The reconciled predecessor let the full updater complete.
The native and embedded helper hashes match the ordinary-open entry above.

The full receipt's changed files passed staged readback checks.
Fresh feedback then verified embedded promotion, listener, HTTP200 assets and
`page: route home`. Settings stayed in `/data/nuvio/`.
The private hardware log holds the exact commands and recovery receipts.

[LOCALLY BUILT] The store zip carries the complete PPSA99997 folder.
The single-install package omits separate boot-payload release assets.
Fresh-jailbreak startup and the eventual published release remain pending.

## Fresh-jailbreak startup, 2026-10-09

[TESTED-ON-CONSOLE] Owner restarted the console, ran Relapse and the normal
services, and left Nuvio closed with no Nuvio helper loaded. Same endpoint.
The complete ordinary-open build then passed receipt-verified feedback:
embedded promotion, bind/listen, packaged HTTP200 and route profileSelection.
The private hardware log records the exact command and full environment tuple.

## Alpha.4 artwork build, 2026-10-09

[LOCALLY BUILT] Replaced the title icon with the supplied 512×512 logo and both
launch images with the supplied 1920×1080 wallpaper. The title content version
is `01.000.004`. `make check`, `NUVIO_WORK_DIR=/tmp/nuvio-alpha4-build make
build` and `NUVIO_WORK_DIR=/tmp/nuvio-alpha4-build make release` passed.

The local `PPSA99997.zip` SHA-256 is
`e50bb82f809f459149374a468087c4ea8d0cd1cb755995d10afa24823063ebce`. Its
`eboot.bin` SHA-256 is
`10794a7e86151ee32157209ab7c58256a53b62cd777985f7e1c41a62918224be`.
The icon SHA-256 is
`d5a3f3d4288081e055cd1013e61f61d2e8ac4af80172cd3c30da1cbf7b4cb3c4`, and both
launch images have SHA-256
`e4d78b2eb802a94c2c7dd02ce8fed16932ebb92541470698cd6f56b32b8ecf66`.

[LOCALLY BUILT] The published alpha.4 `PPSA99997.zip` SHA-256 is
`7173168bded10ebf703502b3db7db99b5a3f2717c6c18ef23456e435eae79e94`. Its
`eboot.bin` SHA-256 is
`55d112286955a973fab49574d97c610ad9ff1b5fe5a89e20938bcdc82dcf770b`. The
release archive passed `unzip -t`. Its icon and launch images match the source
asset hashes above.

[UNKNOWN] We have not installed alpha.4 on the console. Install that exact
`PPSA99997.zip`, run receipt-verified feedback, and record the observed eboot
hash and launch artwork in the private hardware log.


## Playback profile and route return, 2026-10-09

[COMMUNITY] Owner reports alpha.4 returns to "Who's Watching?" after playback.
[SOURCE-VERIFIED] Browser recreation loses the in-memory profile-selection flag.
The startup profile picker runs before route restoration. The original resume
filter also excludes title and stream screens.

The native handoff now saves the selected profile and preceding route before
synchronously saving browser storage. Its return URL includes `nuvioPlaybackReturn=1`.
Startup consumes this saved selection once, checks the active profile still exists,
and restores title, stream or home routes. Ordinary launches retain the picker.
The return snapshot lasts 24 hours. Restoring it refreshes the route timestamp,
so the original 20-minute route limit does not expire during a movie.
Guest startup uses the same return check. Other platforms retain their resume filter.

[LOCALLY BUILT] `make check` passed with 53 tests. The full title build passed:

```sh
NUVIO_WORK_DIR="$PWD/build/playback-return" make build
```

The receipt and update ZIP are in `build/playback-return/`.
`write_store_zip` checked every title file against `build.json` and created the ZIP. ZIP SHA-256: `82b61e1f1bf535f167c8654a2e3a8196d9211a19c2baeaa50a434d94ce86c1e2`.
Eboot SHA-256: `39dbbef26055f352794805e2cb8a9bef106253d1d0a3d67f89c7fb4d8f4daa07`.

[UNKNOWN] Console validation remains pending:

1. Close Nuvio and save the installed receipt and raw eboot backup.
2. Update with the new complete receipt and run fresh UI feedback.
3. Select a profile with Remember last profile disabled, open a title and play.
4. Press Circle. Confirm the same profile and title or stream page return.
5. Play again, then check natural playback end and a failed stream return.
6. Repeat with a PIN profile, guest profile and playback longer than 20 minutes.
7. Close and reopen the title. Confirm the ordinary profile picker still appears.

Use the updater and feedback commands in [Build](BUILD.md#fast-console-loop).
Record console versions, installed hashes and visible results before a release.


### Playback return update installation, 2026-10-09

[TESTED-ON-CONSOLE] The updater closed Nuvio and verified the unmounted title state.
It replaced only eboot and `webui/app.bundle.js`, preserving settings.
The console-side helper verified raw eboot SHA-256 `39dbbef26055f352794805e2cb8a9bef106253d1d0a3d67f89c7fb4d8f4daa07`.
The UI bundle readback matched SHA-256 `c6723b9190ffbac4efee2b3c61eec6f90e28217c0a04758bbcfd9439615f8385`.

Feedback verified the installed eboot, but the launch helper refused startup.
A separate launch attempt reported `running_big_app=49176` and
`launch refused: close the running title or sign in first`.
The private hardware log records commands and rollback files.

[UNKNOWN] Close the active app or sign in, then open Nuvio and perform the
playback return checks above. The launch refusal prevented UI and playback return checks.


### Owner playback return confirmation and alpha.5 package, 2026-10-09

[TESTED-ON-CONSOLE] Owner confirmed "it works" after installing the playback-return
build and testing the reported exit behavior. The installed eboot and UI bundle
hashes are those in the preceding entry. This confirms the reported return fix.
The private hardware log records the environment and installation commands.

[LOCALLY BUILT] Alpha.5 packages the same tested native binary and UI bundle.
Only `sce_sys/param.json` changes to content version `01.000.005`.
`VERSION` is `0.1.0-alpha.5`. The receipt records the updated metadata hash.
The release therefore keeps the tested playback code and browser bundle.
Separate natural-end, long playback and guest/PIN cases remain pending.

[LOCALLY BUILT] Alpha.5 store ZIP SHA-256:
`15310094f8c65dcca45a0714e8c94316898f9afe83412e2438be1a072f4bf486`.
The package retains the recorded eboot and UI hashes.

## EVO 0.12.0 update, 2026-10-10

[SOURCE-VERIFIED] The build pins EVO to the v0.12.0 release commit
`9ee9a5420c73b5be448610e5f0a90a29a75592f3`.
The title retains upstream passthrough, receiver probing and PCM fallback.
Player settings exposes Settings > Audio > Audio Passthrough.
The controller reads this setting when a new stream starts.
The adapter verifies EVO's provider-seek fixes without rewriting them.

The inherited update also pins Nuvio TV and its public login configuration to
1.2.3. SDK v0.43 and pacbrew v0.39 remain fixed.
EVO requires FFmpeg 7.1.1 and its pinned homebrew UI submodule.
The adapter builds FFmpeg from source and unpacks the UI submodule archive.
The FFmpeg compiler prefix now expands the actual SDK directory.

[LOCALLY BUILT] All 58 host tests, documentation and source checks passed.
The complete native build passed with signed-container integrity checks.
The receipt covers 237 title files and eight helpers.
Artifacts and logs remain under `build/evo-0120/`.

| Artifact | SHA-256 |
|---|---|
| `PPSA99997.zip` | `c1055179489bf98410d890e209841b3abc1082ffe8fc6999b10f50a17ec50829` |
| `eboot.bin` | `ec58cbe0f94e4b2db2e61800545218c0664f8efb0307cbaf92a16ff098c7a720` |
| `webui/app.bundle.js` | `84109831940e1e21b85bbc5983f12b8098754a9e9fa9adcabcfe4cda0a91d50e` |

[LOCALLY BUILT] An uncached FFmpeg configure, compile and install passed on macOS.
The release uses content version `01.000.006` and version `0.1.0-alpha.6`.
Build and package commands:

```sh
export NUVIO_WORK_DIR="$PWD/build/evo-0120"
make check
make build
make release
```

[UNKNOWN] Console playback and passthrough for this build remain pending.
The startup result appears in the following session record.
The local archives are held for testing before GitHub publication.

1. Boot firmware 13.60 and run the jailbreak, ShadowMount and loader on 9021.
2. Close foreground apps and confirm the installed predecessor receipt.
3. Update the complete title, preserving `/data/nuvio` and the raw eboot backup.
4. Run fresh UI feedback and confirm the new BUILD line and packaged home route.
5. Play with passthrough disabled. Check sound, pause, seeking and Circle return.
6. Enable Audio Passthrough in Player settings > Settings > Audio.
7. Open a Dolby Digital stream and record the receiver's format display and sound.
8. Repeat with Dolby Digital Plus, DTS and AAC supported by the connected receiver.
9. Switch streams and audio tracks. Check sound resumes and seeking remains usable.
10. Disable passthrough, start another stream and confirm PCM output returns.
11. Close and reopen Nuvio. Check settings and the playback return profile remain correct.

Use the console host and FTP port configured in [Operations](OPERATIONS.md).
Use the same work directory for update and feedback:

```sh
python3 scripts/update.py --previous-receipt config/installed-build.json
python3 scripts/feedback.py --gate ui
```

Record receiver model, HDMI connection, source codec, displayed format and sound.
Record exact installed hashes and the full console environment tuple.
Test TrueHD separately: upstream labels that passthrough path experimental.


## EVO 0.12.0 startup, 2026-10-10

[TESTED-ON-CONSOLE] The alpha.6 player launched on firmware 13.60 and reached the
Nuvio home route. The console model was CFI-1016A 01Y. The build pinned SDK v0.43 and pacbrew v0.39. Resident exploit, loader, HEN and mount-service revisions remain unknown.

Before replacement, the raw player hash and 235 noncontainer files matched the
previous receipt. The update verified the staged and installed player hashes.
The update retained the runtime module without downloading it again.

Eboot SHA-256: `ec58cbe0f94e4b2db2e61800545218c0664f8efb0307cbaf92a16ff098c7a720`.
Browser bundle SHA-256: `84109831940e1e21b85bbc5983f12b8098754a9e9fa9adcabcfe4cda0a91d50e`.

`scripts/feedback.py --gate ui` reported build `9ee9a542-nuvio_1010-0357`, successful
promotion, packaged responses 200 and `page: route home`.
The owner reports startup, playback and exit work. Smaller Penguplay streams seek normally.
Large UsenetStreamer streams can stall after seeking. Pause/resume often restores playback.
The log shows failed chunk reads and repeated HTTP429 responses with six connections.
[Issue #4](https://github.com/bilawalriaz/nuvio-ps5-homebrew/issues/4) tracks the seek problem.
The owner chose to publish alpha.6 and address seeking separately.
An explicit receiver format and codec observation remains pending.


## Network seek fix, 2026-10-10

[SOURCE-VERIFIED] The adapter replaces EVO's parallel HTTP reader with FFmpeg
range reads. Provider headers and playlist behavior remain intact. HTTP429 and
HTTP503 reconnects follow the existing retry budget and respect Retry-After.

[LOCALLY BUILT] The local HTTP test advertised a 256 MiB file with a two-response
limit. Six readers made 222 requests and received 166 rate-limit responses.
The adapted reader made nine requests and received one rate-limit response.
All five adapted range seeks passed. A permanently limited endpoint failed after
two requests in 1.2 seconds. The probe and adapter passed ASan and UBSan checks.
Host FFmpeg was 9.0.1. The console build uses pinned FFmpeg 7.1.1.

[TESTED-ON-CONSOLE] A separate I/O probe on firmware 13.60 opened the same
22 GB UsenetStreamer source and passed nine seeks, including 371.664 and 835.083 seconds.
The probe used the adapted source and the pinned console FFmpeg libraries.
Probe SHA-256: `d02f7ae36f6fee34cbb43444a390a123b9f600e8d690892112d54bdfa3ed13ff`.

A temporary development build enabled EVO's existing remote controls.
The player decoded HEVC10 at 3840x2160 and resumed after four absolute seeks.
A D-pad Right command completed a scrub seek, followed by continued playback.
Circle stopped playback. Fresh logs contained no HTTP429 response.
The decoder closed with 626 output frames and `fatal=0` on the second run.
Cumulative seek counters reported ten accepted seeks and zero failures.
Development eboot SHA-256: `563f7b87114da53bafc29fcc6bb32dcaeb7008b74cb629b3408c29f8a30be700`.

The normal alpha.7 build excludes development controls.
The restored player launched with build `9ee9a542-nuvio_1010-0436`.
Fresh feedback confirmed packaged HTTP200 responses and the profile-selection route.
Its eboot SHA-256 is `e800b9ac03f47662bb9452bacb8fe074dc53579c4dc80d6b74c0f641c0985d26`.
Console model: CFI-1016A 01Y. SDK v0.43 and pacbrew v0.39 remained fixed.
Resident exploit, loader, HEN and helper revisions remain unknown.
Visible picture, sound and browsing-return observations for this build remain pending.
