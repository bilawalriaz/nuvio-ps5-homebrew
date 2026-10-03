# Operations

## Prepare the console and the computer

1. Jailbreak the console for the current boot.
2. Check the console firmware without installing an update.
3. Start the ELF loader, the FTP service and ShadowMount.
4. Close other applications before you launch Nuvio with a helper.
5. Keep the computer and the console on the same network.
6. Install the release archive, or build from source as described in [Build](BUILD.md).

The tested target is firmware 13.60. Record the loader and HEN versions when you
can read them. A reboot clears the jailbreak and the resident helpers.

## Addresses

Replace every angle-bracket value below with your own value. Use the ports of the
services that run on your console. The scripts never scan for a console.

```sh
export PS5_HOST="<console-address>"
export PS5_ELF_PORT="<loader-port>"
export PS5_FTP_PORT="<ftp-port>"
export NUVIO_UI_HOST="<computer-lan-address>"
export NUVIO_UI_ORIGIN="http://${NUVIO_UI_HOST}:4173"
```

The test session used loader port 9021 and FTP port 1337. Port 4173 is the Nuvio
UI server default. Keep these values in your terminal or in an ignored local
file. The scripts read exported variables and do not read `config/`.

The FTP scripts log in as `anonymous` by default. Set `PS5_FTP_USER` and
`PS5_FTP_PASS` for an account. Keep both values private.

## Start the UI server

Run this command in its own terminal:

```sh
python3 scripts/serve.py \
  --host "$NUVIO_UI_HOST" \
  --origin "$NUVIO_UI_ORIGIN" \
  --test-clip
```

Keep the terminal open while you use Nuvio, and keep the computer awake. The
server publishes `build/ui` and the generated test addon. It never publishes the
repository or the native title directory.

`--test-clip` writes a 15 second test video when the clip is absent. It needs
host FFmpeg. Omit the flag if you do not want the clip. For another port, pass
`--port` and use the same port inside `--origin`.

Check the host page:

```sh
curl --fail "$NUVIO_UI_ORIGIN/" -o /dev/null
```

A successful request proves the HTTP server answers on the computer. It does not
prove that the console reaches the server.

## Install from the release archive

1. Download and unpack `PPSA99997.zip`.
2. Copy the `PPSA99997` folder to `/data/homebrew/` on the console over FTP.
3. Push `permission-watcher.elf` to the ELF loader once for this boot.
4. Write `/data/nuvio/nuvio.conf` with your server address.
5. Start the UI server.
6. Launch Nuvio from the console home screen.

The watcher reports:

```text
NUVIO permission watcher ready: PPSA99997 only, FW 13.60
```

`nuvio.conf` holds three lines:

```text
host=<computer-lan-address>
port=4173
https=0
```

ShadowMount picks up the new folder and registers it as a title. Launch the app
after registration completes.

## Install from a source build

Use this procedure when the title and its settings do not exist. The installer
refuses an existing installation path, an existing staging path and an existing
`/data/nuvio/nuvio.conf`.

1. Start the UI server.
2. Push the permission watcher once for this boot.
3. Wait for the watcher ready message.
4. Install the title.
5. Check the title information.
6. Launch after registration completes.

```sh
python3 scripts/upload.py --file build/permission-watcher.elf
python3 scripts/install.py --origin "$NUVIO_UI_ORIGIN"
python3 scripts/upload.py --file build/control-2.elf
python3 scripts/upload.py --file build/control-3.elf
```

`install.py` checks local hashes before it contacts the console. It stages files
below `/data/homebrew/ps5-homebrew-dev`, checks the staged bytes, then moves the
folder to `/data/homebrew/PPSA99997`. `control-4` hashes the generated runtime on
the console, which avoids the etaHEN FTP runtime download problem.

Add `--from-release <unpacked-release-dir>` to install the files from a release
archive instead of a source build:

```sh
python3 scripts/install.py \
  --origin "$NUVIO_UI_ORIGIN" \
  --from-release /path/to/unpacked-release
```

Registration is asynchronous. `control-1` needs a ShadowMount response with
`present:true`. `control-2` must report `installed:true` before launch.
`control-3` refuses a resident application or a missing signed-in user. A launch
response needs visible output or console logs to count as a result.

Save the installed receipt after a successful install:

```sh
cp build/build.json config/installed-build.json
```

## Install the helpers with PS5 Payload Manager

Every release carries `payloads.json`. It lists the helper payloads with their
SHA-256 hashes.

1. Open the Payload Manager dashboard.
2. Open Settings, then Manage Sources.
3. Add the `payloads.json` URL from the release.
4. Load the Nuvio helpers from the dashboard.

Payload Manager validates each download against the recorded hash.

## Start after a reboot

1. Jailbreak the console again.
2. Start the loader, the FTP service and ShadowMount.
3. Start the same UI server origin.
4. Push one permission watcher for this boot.
5. Launch Nuvio from its icon or with `control-3`.

Push one watcher per boot. The watcher stays resident after the host stops
reading its output. A helper from the previous boot no longer runs.

## Update an installed title

1. Save the receipt for the installed build.
2. Close Nuvio through the PS5 app switcher.
3. Keep Nuvio closed during the update.
4. Build the candidate version.
5. Run the updater with the installed receipt.
6. Save the new receipt after the updater succeeds.
7. Start the UI server with the candidate UI.
8. Launch Nuvio.
9. Run the checks in [Validation](VALIDATION.md#acceptance-procedure).

```sh
python3 scripts/update.py \
  --previous-receipt config/installed-build.json
cp build/build.json config/installed-build.json
python3 scripts/upload.py --file build/control-3.elf
```

The updater needs an installed, unmounted folder title. It checks the candidate
files and the permitted changes before it replaces app files. It checks each
changed predecessor against the old receipt, saves a verified backup, and checks
each staged replacement before it renames it.

The permitted changes are eboot, launch images, icon, loading RML and wordmark.
The updater rejects runtime changes, removed inventory entries and unrelated
assets. An interrupted update can leave a partial set of new files. Use
[recovery](TROUBLESHOOTING.md#restore-an-interrupted-update) to reconcile it.

## Copy synced addons into native EVO

Close the title before you change its stored addon list. Run the updater with the
installed receipt:

```sh
python3 scripts/update.py \
  --previous-receipt config/installed-build.json \
  --sync-addons
```

The script reads the active Nuvio profile from its stored browser state. It
copies that profile's addon manifests into `/data/nuvio/addons.json` and updates
an existing `/data/evoplayer` settings directory when one is present. It never
creates a separate EVO application.

Native limits are 12 addons and fewer than 512 bytes per manifest URL. The script
rejects longer lists. It keeps addon URLs and tokens out of printed output.
Private browser backups stay under `/data/nuvio/webui`.

To add the local test addon without the console keyboard:

```sh
python3 scripts/update.py \
  --previous-receipt config/installed-build.json \
  --sync-addons \
  --test-addon "$NUVIO_UI_ORIGIN/ps5-test/manifest.json"
```

Keep the test UI server running while you use that addon.

## Change the UI origin

Keep the original origin unless you need to change it. The provider stores the
host, port and protocol in `/data/nuvio/nuvio.conf`. Changing the server command
alone does not change the console configuration.

Close the title before you edit the file through FTP. Keep a private copy of the
old file. Use the new origin's host and port with `https=0`. Start the server at
that origin before you relaunch.

Stored browser state uses the origin host and port in its filename. A new origin
can select different saved state, so keep a copy of the old state.
