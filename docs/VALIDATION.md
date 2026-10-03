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
