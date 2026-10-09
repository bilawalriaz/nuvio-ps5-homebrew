# Troubleshooting

## Stuck on “Opening Nuvio”

Check the current boot's jailbreak, ShadowMount and ELF loader on port 9021.
Check that `/data/homebrew/PPSA99997/webui/` exists.
The single-install title loads its helper automatically and serves the page itself.
Release 0.1.0-alpha.2 needs its separate `nuvio.elf` boot payload.
Collect a private copy of `/data/nuvio/evo.log` if the splash remains.

## Collect evidence first

Record the exact visible error and the installed eboot hash. Record whether the
problem starts before playback, during a seek or after exit. Keep the receipt for
the installed build. A host build or a completed transfer cannot show what the
console displays.

Native logs can hold private stream URLs and tokens. Read a local copy before you
share an excerpt, and remove addon URLs, account details and signed stream
parameters.

## Browser error WV-109145-0

In the first test this error followed a proxy bind failure. The host preflight
answered, but the loopback listener returned `errno=13`. The payload privilege
grant resolves that failure. The error code on its own does not identify a DNS or
TLS problem.

1. Check that the current boot's ELF loader listens on port 9021.
2. Check the UI origin in `/data/nuvio/nuvio.conf` (default `127.0.0.1`).
3. Check for a listener failure in a private native log.
4. Check that the title folder carries `webui/`.
5. Close and reopen Nuvio after the loader starts.

Use the [startup procedure](OPERATIONS.md#start-after-a-reboot) after a reboot.

## QR login or focused X fails

A source-only Nuvio build lacks the official TV login configuration. The pinned
official package supplies the public values during the build. The PS5 input
script bridges the browser pointer and the D-pad focus.

1. Check that the console loads `nuvio.env.js` and `ps5-input.js` from the current server.
2. Check that the official package checksum matches `deps.lock`.
3. Check whether the highlighted element activates when you press X.
4. Restart the title with the rebuilt UI if it still shows old assets.

Keep the anonymous browser key. Do not replace it with a privileged service key.
Keep private account state out of reports.

## Playback returns to browsing immediately

Check the source access result before you check the decoder. One source returned
HTTP 403, and the decoder never started. A source can require a valid signed URL
or refuse access.

Try the installed PS5 Playback Test addon when it is present. Look for
`video decoder opened` in the private log and note the backend and the dimensions
without publishing the source URL. A request failure and a decoder failure need
different evidence.

## Seeking freezes

The first provider seek guard rejected an empty local media path, and the
controller still entered the seeking state. The corrected build accepts valid
provider demuxers and announces only accepted seeks. See the
[artifact history](VALIDATION.md#artifact-history).

1. Check the installed eboot hash against the corrected receipt.
2. Look for the seek request and its result in the private log.
3. Look for a later `SEEK_SETTLE` line.
4. Note whether the picture and the audio resume on the TV.

The recorded baseline seek settled in 1107 milliseconds, and a later corrected
exit build settled a seek in 1662 milliseconds. Those values describe those
attempts only. Seek time differs per stream.

## Circle shows Opening Nuvio but the video stays active

The first branded shell hid the EVO exit confirmation. A second Circle canceled
that confirmation and returned to video. The corrected adapter stops playback
that started from Nuvio directly. It also keeps active playback overlays.

Check the installed hash against the corrected exit artifact. The log should show
decoder closure followed by browser reopening. Check the TV for the expected
Nuvio page. Console reopening alone does not show which page appears.

## A helper reports transfer success without a result

The uploader reports bytes sent before it reads helper output, and it stops
capturing after an idle timeout or an output limit. A resident helper can keep
running after capture ends, and a failed payload can also produce no output.

Check the expected response for that helper. Treat the transfer itself as
transport, not execution. Do not push the payload again to compensate for missing
output. If the console rebooted, run the fresh-boot procedure.

## The updater refuses the title

| Message or state | Required action |
|---|---|
| `mounted:true` | Close the title through the app switcher. Check `control-2` again. |
| Installed predecessor mismatch | Compare the console files with the receipt for the actual installed build. |
| Eboot receipt mismatch | Run `control-5.elf` and compare its on-console raw hash with the installed receipt. FTP `RETR` transforms PS5 containers. |
| Local receipt mismatch | Restore matching candidate files or build a new candidate. |
| Staging path already exists | Inspect the interrupted stage before you replace or remove it. |
| Changes exceed the allowlist | Prepare a reviewed migration for those files. |
| Receipt identity or inventory mismatch | Use matching title receipts and check whether the candidate removes files. |

The updater performs no general migration and no automatic rollback. Do not
bypass its checks while ShadowMount keeps the title mounted, and do not edit a
receipt hash to hide a mismatch.

## Restore an interrupted update

The updater replaces individual files, so an update is not atomic. An
interruption can leave old, new and staged files together.

1. Keep Nuvio closed.
2. Run `control-2`.
3. Require `mounted:false`.
4. Keep both receipts and a private list of the current file hashes.
5. Inspect each changed file through FTP.
6. Match each file to the old receipt, the new receipt, or neither.
7. Find the verified backup for each replaced file.
8. Restore the intended file set through FTP.
9. Check every restored hash before launch.

The updater names ordinary-file backups with the previous hash and the flattened
relative path. `control-5.elf` stores raw eboot backups as
`nuvio-eboot-backup-<sha256>.bin` below `/data/homebrew/ps5-homebrew-dev`. Do not
verify or restore these container files with FTP `RETR`. Use on-console hashing
and rename the matching backup back to `/data/homebrew/PPSA99997/eboot.bin`.

Restore only files that the matching receipts list, and keep `/data/nuvio` with
its private account state. Do not replace the runtime to diagnose an eboot
update. Record the hashes of staging files before you remove them.

## Report a failure

Include the firmware, the console model, the source pins, the eboot hash and the
expected behavior. Include the exact command with private addresses and
credentials removed. State whether the evidence comes from a host test, a console
log or the TV. Add a short filtered log excerpt and the recovery action.
