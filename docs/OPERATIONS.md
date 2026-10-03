# Operations

## Prepare the console

1. Jailbreak the console for the current boot.
2. Check the console firmware without installing an update.
3. Start the ELF loader, the FTP service and ShadowMount.
4. Close other applications before you launch Nuvio with a helper.
5. Install the release archive, or build from source as described in [Build](BUILD.md).

The tested target is firmware 13.60. Record the loader and HEN versions when you
can read them. A reboot clears the jailbreak and the resident helpers.

## Addresses

Replace every angle-bracket value below with your own value. Use the ports of the
services that run on your console. The scripts never scan for a console.

```sh
export PS5_HOST="<console-address>"
export PS5_ELF_PORT="<loader-port>"
export PS5_FTP_PORT="<ftp-port>"
```

The test session used loader port 9021 and FTP port 1337. Keep these values in
your terminal or in an ignored local file. The scripts read exported variables and
do not read `config/`.

The FTP scripts log in as `anonymous` by default. Set `PS5_FTP_USER` and
`PS5_FTP_PASS` for an account. Keep both values private.

## Serve the UI during development

The shipped app serves its own interface from the title folder. Nothing on the
network has to run. Use `scripts/serve.py` only while iterating on the browser
bundle, so a UI change does not need a push to the console:

```sh
python3 scripts/serve.py \
  --host "<computer-lan-address>" \
  --origin "http://<computer-lan-address>:4173" \
  --test-clip
```

Keep the terminal open while you use that origin. The server publishes `build/ui`
and the generated test addon. It never publishes the repository or the native
title directory. Point `/data/nuvio/nuvio.conf` at that origin to use it. The
default origin in [Change the UI origin](#change-the-ui-origin) uses the console
server instead.

`--test-clip` writes a 15 second test video when the clip is absent. It needs
host FFmpeg. Omit the flag if you do not want the clip. For another port, pass
`--port` and use the same port inside `--origin`.

Check the host page:

```sh
curl --fail "http://<computer-lan-address>:4173/" -o /dev/null
```

A successful request proves the HTTP server answers on the computer. It does not
prove that the console reaches the server.

## Install from the release archive

1. Download and unpack `nuvio-ps5-<version>.zip` (or the store `PPSA99997.zip`).
2. Copy the `PPSA99997` folder to `/data/homebrew/` on the console over FTP.
3. Push `nuvio.elf` to the ELF loader once for this boot.
4. Launch Nuvio from the console home screen.

The payload reports:

```text
NUVIO payload ready: PPSA99997 only, FW 13.60
NUVIO ui: serving /data/homebrew/PPSA99997/webui on 127.0.0.1:4173
```

`nuvio.conf` carries the console origin on the first boot when the file is
absent:

```text
host=127.0.0.1
port=4173
https=0
```

ShadowMount picks up the new folder and registers it as a title. Launch the app
after registration completes.

## Install from a source build

Use this procedure when the title and its settings do not exist. The installer
refuses an existing installation path, an existing staging path and an existing
`/data/nuvio/nuvio.conf`.

1. Push `nuvio.elf` once for this boot.
2. Wait for the payload ready message.
3. Install the title.
4. Check the title information.
5. Launch after registration completes.

```sh
python3 scripts/upload.py --file build/nuvio.elf
python3 scripts/install.py
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
python3 scripts/install.py --from-release /path/to/unpacked-release
```

Registration is asynchronous. `control-1` needs a ShadowMount response with
`present:true`. `control-2` must report `installed:true` before launch.
`control-3` refuses a resident application or a missing signed-in user. A launch
response needs visible output or console logs to count as a result.

Save the installed receipt after a successful install:

```sh
cp build/build.json config/installed-build.json
```

## Install the payload with PS5 Payload Manager

Every release carries `payloads.json`. It lists the single payload `nuvio.elf`
with its SHA-256 hash.

1. Open the Payload Manager dashboard.
2. Open Settings, then Manage Sources.
3. Add the `payloads.json` URL from the release.
4. Load the Nuvio payload from the dashboard.

Payload Manager validates the download against the recorded hash.

## Start after a reboot

1. Jailbreak the console again.
2. Start the loader, the FTP service and ShadowMount.
3. Push `nuvio.elf` once for this boot.
4. Launch Nuvio from its icon or with `control-3`.

Push one payload per boot. It stays resident after the host stops reading its
output and serves the UI until the console restarts. A payload from the previous
boot no longer runs.

## Update an installed title

1. Save the receipt for the installed build.
2. Close Nuvio through the PS5 app switcher.
3. Keep Nuvio closed during the update.
4. Build the candidate version.
5. Run the updater with the installed receipt.
6. Save the new receipt after the updater succeeds.
7. Launch Nuvio.
8. Run the checks in [Validation](VALIDATION.md#acceptance-procedure).

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

The permitted changes are eboot, launch images, icon, loading RML, wordmark and
the `webui/` folder (the browser UI ships inside the title). The updater rejects
runtime changes, removed inventory entries and unrelated assets. An interrupted
update can leave a partial set of new files. Use
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

To add a local test addon without the console keyboard:

```sh
python3 scripts/update.py \
  --previous-receipt config/installed-build.json \
  --sync-addons \
  --test-addon "http://<computer-lan-address>:4173/ps5-test/manifest.json"
```

Keep `scripts/serve.py` running while you use that addon.

## Change the UI origin

The default origin is the console's own server: `127.0.0.1:4173` in
`/data/nuvio/nuvio.conf`. `nuvio.elf` writes it on the first boot when the file is
absent. Leave it in place for normal use.

To test a development UI served from the computer, close the title and edit
`/data/nuvio/nuvio.conf` over FTP to that computer's host and port with
`https=0`. Keep a private copy of the old file. Start `scripts/serve.py` at that
origin before you relaunch, and restore `127.0.0.1` to return to the console
server.

Stored browser state uses the origin host and port in its filename. A new origin
can select different saved state, so keep a copy of the old state.
