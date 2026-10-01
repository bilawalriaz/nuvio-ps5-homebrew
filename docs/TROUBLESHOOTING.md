# Troubleshooting

## Collect evidence first

Record the exact visible error and the installed eboot hash.
Record whether the problem starts before playback, during a seek or after exit.
Keep the receipt for the installed build.
A host build or TCP transfer cannot establish visible console behavior.

Raw native logs can contain private stream URLs and tokens.
Inspect a local copy before sharing any excerpt.
Remove addon URLs, account identifiers and signed stream parameters.
Do not commit raw logs or stored browser state.

## Browser error WV-109145-0

In the first test, this error followed a proxy bind failure.
The host preflight answered, but the loopback listener returned `errno=13`.
The permission helper resolved that specific failure.
The error code alone does not identify a DNS or TLS problem.

1. Check that the host UI server still runs.
2. Check the configured UI origin in `/data/nuvio/nuvio.conf`.
3. Check for a listener failure in a private native log.
4. Check whether one permission watcher runs for this boot.
5. Require the ready message when uploading a watcher after a fresh jailbreak.

Use the [startup procedure](OPERATIONS.md#start-after-a-reboot) after a reboot.
Do not change exploit DNS to repair an observed permission failure.
Do not assume every occurrence of this browser error has the same cause.

## QR login or focused X fails

A source-only Nuvio build lacks the official TV login configuration.
The pinned official package supplies the public values during the build.
The PS5 input script handles the browser pointer and D-pad focus difference.

1. Check that the console loads `nuvio.env.js` and `ps5-input.js` from the current server.
2. Check that the official package checksum matches `deps.lock`.
3. Check whether the highlighted element activates when you press X.
4. Restart the title with the rebuilt UI if it still displays old assets.

Do not replace the anonymous browser key with a privileged service key.
Keep private account state out of reports.

## Playback returns to browsing immediately

Check the source access result before checking the decoder.
An observed HTTP 403 prevented one source from opening.
The decoder did not start for that failed request.
A source can require a valid signed URL or refuse access.

Try the installed PS5 Playback Test addon, if present.
Check for `video decoder opened` in the private log.
Check its backend and dimensions without publishing the source URL.
A request failure and a decoder failure need different evidence.

## Seeking freezes

The initial provider seek guard rejected an empty local media path.
The controller still entered the seeking state.
The corrected build accepts valid provider demuxers and announces only accepted seeks.
See the [artifact history](VALIDATION.md#artifact-history).

1. Check the installed eboot hash against the corrected receipt.
2. Check for a seek request and its result in the private log.
3. Check for a later `SEEK_SETTLE` line.
4. Record whether picture and audio resume on the TV.

The recorded baseline seek settled in 1107 milliseconds.
A later corrected exit build settled a seek in 1662 milliseconds.
These values describe those attempts only.
Do not infer a fixed seek delay for all streams.

## Circle shows Opening Nuvio but video remains active

The first branded shell hid EVO's exit confirmation.
A second Circle canceled that confirmation and returned to video.
The corrected adapter directly stops playback started from Nuvio.
It also preserves active playback overlays.

Check the installed hash against the corrected exit artifact.
The log should show decoder closure followed by browser reopening.
The TV must show the expected Nuvio page for visual acceptance.
Console reopening alone does not establish the displayed route.

## A helper reports transfer success without a result

The uploader reports bytes sent before it reads helper output.
Its capture ends after an idle timeout or output limit.
A resident helper can continue after capture ends.
A failed or stopped payload can also produce no further output.

Check the expected response for the specific helper.
Do not use a successful transfer as execution evidence.
Do not repeatedly upload resident watchers to compensate for missing output.
If the console rebooted, perform the fresh-boot procedure.

## The updater refuses the title

| Message or state | Required action |
|---|---|
| `mounted:true` | Close the title through the app switcher. Check control-2 again. |
| Installed predecessor mismatch | Compare the console files with the receipt for the actual installed build. |
| Local receipt mismatch | Restore matching candidate files or build a new candidate. |
| Staging path already exists | Inspect the interrupted stage before replacing or removing it. |
| Changes exceed the allowlist | Prepare a reviewed migration for those files. |
| Receipt identity or inventory mismatch | Use matching title receipts. Check whether the candidate removes files. |

The updater does not perform a general migration or automatic rollback.
Do not bypass its checks while ShadowMount keeps the title mounted.
Do not edit a receipt hash merely to suppress a mismatch.

## Restore an interrupted update

The updater replaces individual files.
It does not make the complete update atomic.
An interruption can leave old, new and staged files together.

1. Keep Nuvio closed.
2. Run control-2.
3. Require `mounted:false`.
4. Preserve both receipts and a private list of current file hashes.
5. Inspect each changed file through FTP.
6. Match each file to the old receipt, new receipt or neither receipt.
7. Locate the verified backup for each replaced file.
8. Restore the intended file set through a deliberate FTP procedure.
9. Check all restored hashes before launch.

The current updater names backups with the previous hash and flattened relative path.
For example, an eboot backup ends in `-eboot.bin`.
A staged replacement ends in `.nuvio-update`.
All these app backups remain below `/data/homebrew/ps5-homebrew-dev`.

Restore only files listed in the matching receipts.
Preserve `/data/nuvio` and its private account state.
Do not download or replace the runtime merely to diagnose an eboot update.
Do not remove staging files before recording their hashes.
The helper for runtime hashing checks the first-install stage only.
It does not hash an arbitrary installed module.

## Report a failure

Include the firmware, console model, source pins, eboot hash and expected behavior.
Include the exact command with private addresses and credentials removed.
State whether evidence comes from a host test, console log or TV observation.
Include a short filtered log excerpt and the recovery action.
Do not claim support for another firmware from a successful build.
