# Operations

## Prepare the console and host

1. Jailbreak the console for the current boot.
2. Check the console firmware without installing an update.
3. Start the ELF loader, etaHEN FTP and ShadowMount.
4. Close other applications before launching Nuvio with a helper.
5. Keep the computer and console on a reachable LAN.
6. Build Nuvio as described in [Build](BUILD.md).

The documented test target is firmware 13.60.
The exact resident loader and HEN versions remain unknown in the first session.
Record those versions when you can establish them.
A reboot clears the jailbreak and resident helpers.

## Set explicit addresses

Replace every angle-bracket value below with your own value.
Do not run the examples with the placeholder text.
Use the ports configured in the running services.
The scripts do not discover a console address.

```sh
export PS5_HOST="<console-address>"
export PS5_ELF_PORT="<loader-port>"
export PS5_FTP_PORT="<ftp-port>"
export NUVIO_UI_HOST="<computer-lan-address>"
export NUVIO_UI_ORIGIN="http://${NUVIO_UI_HOST}:4173"
```

The test session used loader port 9021 and FTP port 1337.
These observations do not identify every loader or FTP configuration.
Port 4173 follows the Nuvio host server default.

Keep these values in the terminal or an ignored local file.
The scripts read exported variables.
They do not automatically read files in `config/`.

The FTP scripts use anonymous login by default.
For a configured account, set `PS5_FTP_USER` and `PS5_FTP_PASS` privately.
Do not publish either value.

## Start the UI server

Run this command in a separate terminal:

```sh
python3 scripts/serve.py \
  --host "$NUVIO_UI_HOST" \
  --origin "$NUVIO_UI_ORIGIN" \
  --test-clip
```

Keep this terminal running during Nuvio use.
The computer must remain awake and reachable.
The server serves `build/ui` and the generated test addon.
It does not serve the source repository or native title directory.

`--test-clip` creates a 15-second test video if the clip is absent.
This option requires host FFmpeg.
Omit it if you do not need the test clip.
For a different server port, set `--port` and use the same port in `--origin`.

Check the host page:

```sh
curl --fail "$NUVIO_UI_ORIGIN/" -o /dev/null
```

A successful host request checks the HTTP server.
It does not establish PS5 browser access.
The browser reaches the server through EVO's console proxy.

## First installation

Use this procedure only when the title and its settings do not exist.
The installer refuses existing installation and staging paths.
It also refuses an existing `/data/nuvio/nuvio.conf`.

1. Start the UI server.
2. Upload the permission watcher once for this boot.
3. Require the watcher ready message.
4. Install the title.
5. Check the title information.
6. Launch after registration completes.

```sh
python3 scripts/upload.py --file build/permission-watcher.elf
python3 scripts/install.py --origin "$NUVIO_UI_ORIGIN"
python3 scripts/upload.py --file build/control-2.elf
python3 scripts/upload.py --file build/control-3.elf
```

The watcher reports:

```text
NUVIO permission watcher ready: PPSA99997 only, FW 13.60
```

The installer verifies local hashes before contacting the console.
It stages files below `/data/homebrew/ps5-homebrew-dev`.
It checks staged bytes before moving the folder to `/data/homebrew/PPSA99997`.
Control-4 checks the generated runtime on the console.
This avoids the etaHEN FTP runtime download problem.

Registration is asynchronous.
Control-1 needs a successful ShadowMount response with `present:true`.
Control-2 must report `installed:true` before launch.
Control-3 refuses a resident application or a missing signed-in user.
A launch response needs visible output or console logs for a complete result.

After a successful installation, save the installed receipt:

```sh
cp build/build.json config/installed-build.json
```

Do not replace this receipt with a later build until that build reaches the console.

## Start after a reboot

1. Jailbreak the console again.
2. Start the loader, FTP service and ShadowMount.
3. Start the same UI server origin.
4. Upload one permission watcher for this boot.
5. Launch Nuvio from its icon or control-3.

Do not upload multiple watchers during one boot.
The watcher stays resident after the host stops reading its output.
Do not assume a helper from the previous boot still runs.

## Update an installed title

1. Save the receipt for the currently installed build.
2. Close Nuvio through the PS5 app switcher.
3. Leave Nuvio closed during the update.
4. Build the candidate version.
5. Run the updater with the installed receipt.
6. Save the new receipt after the updater succeeds.
7. Start the UI server with the candidate UI.
8. Launch Nuvio.
9. Complete the checks in [Validation](VALIDATION.md#acceptance-procedure).

```sh
python3 scripts/update.py \
  --previous-receipt config/installed-build.json
cp build/build.json config/installed-build.json
python3 scripts/upload.py --file build/control-3.elf
```

The updater requires an installed, unmounted folder title.
It checks candidate files and permitted changes before replacing app files.
It checks each changed predecessor against the old receipt.
It saves a verified backup before replacing each file.
It verifies each staged replacement before renaming it.

The permitted changes are eboot, launch images, icon, loading RML and wordmark.
The updater rejects runtime changes, removed inventory entries and unrelated assets.
An interrupted update can leave a partial set of new files.
Do not launch that partial installation.
Use [recovery](TROUBLESHOOTING.md#restore-an-interrupted-update) to reconcile it.

## Copy synced addons into native EVO

Close the title before changing its stored addon list.
Use the updater with the installed receipt:

```sh
python3 scripts/update.py \
  --previous-receipt config/installed-build.json \
  --sync-addons
```

The script reads the active Nuvio profile from its stored browser state.
It copies that profile's addon manifests into `/data/nuvio/addons.json`.
It also updates an existing `/data/evoplayer` settings directory, if present.
It does not create a separate EVO application.

Native limits are 12 addons and fewer than 512 bytes per manifest URL.
The script rejects lists that exceed those limits.
It keeps addon URLs and tokens out of printed output.
Private browser backups remain under `/data/nuvio/webui`.

To add the local test addon without using the console keyboard:

```sh
python3 scripts/update.py \
  --previous-receipt config/installed-build.json \
  --sync-addons \
  --test-addon "$NUVIO_UI_ORIGIN/ps5-test/manifest.json"
```

This option adds the test addon to both stored Nuvio and native lists.
Keep the test UI server running when selecting that addon.

## Change the UI origin

Keep the original UI origin unless you need to change it.
The provider stores host, port and protocol in `/data/nuvio/nuvio.conf`.
Changing only the host server command does not change the console configuration.

Close the title before editing this file through FTP.
Preserve a private copy of the old file.
Use the new origin's host and port with `https=0`.
Start the server at that origin before relaunching.

Stored browser state uses the origin's host and port in its filename.
A new origin can select different saved state.
Preserve the old state before changing the origin.
