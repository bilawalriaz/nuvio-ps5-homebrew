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

Use `scripts/serve.py` to preview the browser bundle on your computer.
The title-local build reads its installed `webui/` folder on the PS5.
Use the verified updater to install browser changes for console testing.

## Install from the release archive

Follow [Getting started](GETTING_STARTED.md) for the single-install build.
Copy `PPSA99997/` into `/data/homebrew/`, refresh ShadowMount and open the tile.
The title loads its embedded helper through the current boot's ELF loader on 9021.
Release 0.1.0-alpha.2 needs the older separate `nuvio.elf` boot payload.

## Install from a source build

Use this procedure when the title and its settings do not exist. The installer
refuses an existing installation path, an existing staging path and an existing
`/data/nuvio/nuvio.conf`.

1. Build with `make build`.
2. Install the title.
3. Check the title information.
4. Launch after registration completes.

```sh
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

## Start after a reboot

1. Jailbreak the console again.
2. Start ShadowMount and the ELF loader on port 9021.
3. Open Nuvio from its tile or with `control-3`.

The single-install title loads its embedded permission helper automatically.

## Update an installed title

1. Save the receipt for the installed build.
2. Let the updater close Nuvio automatically.
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
files and the permitted changes before it replaces app files. For `eboot.bin`,
`control-5.elf` hashes the installed bytes on the console, saves an on-console
rollback copy, and verifies the staged bytes before the updater renames them.
FTP `RETR` transforms PS5 containers, so the updater does not use it to verify
the eboot. It verifies other changed files through staged readback.

The permitted changes are eboot, launch images, icon, loading RML, wordmark and
the `webui/` folder (the browser UI ships inside the title). The updater rejects
runtime changes, removed inventory entries and unrelated assets. An interrupted
update can leave a partial set of new files. Use
[recovery](TROUBLESHOOTING.md#restore-an-interrupted-update) to reconcile it.

## Development feedback

Close Nuvio, update the build, then run the feedback command:

```sh
make check
make build
python3 scripts/update.py --previous-receipt config/installed-build.json
make feedback
```

The command checks helper hashes and the installed eboot before launch.
It reports only startup events added after launch.
It finishes when the listener accepts a connection and Nuvio reports a page route.
Private stream URLs and login values stay out of its output.

Use `--gate loopback` to check listener permissions separately from page loading:

```sh
python3 scripts/feedback.py --gate loopback
```

The command loads only title-information, hash and launch controls.
It never loads the Nuvio permission helper or UI server.
Keep the normal boot payload running for the current release's UI check.
Use a fresh jailbreak without that payload for the unpromoted diagnostic.

Save the new installed receipt after the updater succeeds.
Record TV observations and playback tests separately in [Validation](VALIDATION.md).

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

## Browser storage origin

The title serves its packaged `webui/` through its own loopback listener.
The provider's configured host and port remain the browser-storage key for existing accounts.
Keep the existing `/data/nuvio/nuvio.conf` and browser state when updating.

## Close Nuvio for development

```sh
make close
```

Build once to create the receipt-verified close helper. The command closes only
the unique Nuvio process and verifies an unmounted title. It does not
terminate another foreground app. New build receipts let update and feedback
close Nuvio automatically before their mount checks. Older receipts need the
existing manual close procedure.
