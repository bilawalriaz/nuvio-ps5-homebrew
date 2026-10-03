# Nuvio PS5

Nuvio PS5 runs Nuvio TV on a jailbroken PlayStation 5 and plays streams with EVO
Player's native engine. Nuvio supplies the account, catalogue and addon screens.
EVO supplies the controller input, audio and hardware video decoding.

This is a community project with no connection to Sony, NuvioMedia or EVO Player.
Version `0.1.0-alpha.1`.

## What it does

- Shows Nuvio TV in the PS5 system browser, served from your own computer.
- Hands a stream to the native engine for hardware decoding.
- Reopens the browser on your last Nuvio page when playback stops.
- Moves browser focus with the D-pad, so X activates the item you selected.

## Requirements

- A retail PS5 on firmware 13.60 with a jailbreak for the current boot. Keep the
  console on 13.60.
- An ELF loader, an FTP service and ShadowMount running on the console.
- A computer on the same network that serves the Nuvio UI while you use the app.
  Keep it awake and reachable.
- macOS with Xcode command-line tools, Homebrew LLVM and Node.js, only to build
  the native title yourself.

## Install

1. Download `PPSA99997.zip` and `permission-watcher.elf` from the
   [latest release](https://github.com/bilawalriaz/nuvio-ps5-homebrew/releases/latest).
2. Unpack the archive.
3. Copy the `PPSA99997` folder to `/data/homebrew/` on the console over FTP.
4. Push `permission-watcher.elf` to the ELF loader once for this boot.
5. Write your server address to `/data/nuvio/nuvio.conf`:

   ```text
   host=<computer-lan-address>
   port=4173
   https=0
   ```

6. Start the UI server on the computer. See [Operations](docs/OPERATIONS.md).
7. Launch Nuvio from the console home screen.

The release also carries the other helpers, `payloads.json` for
[PS5 Payload Manager](https://github.com/itsPLK/ps5-payload-manager), and
`nuvio-ps5-<version>.zip` with the UI and the full source. Add the
`payloads.json` URL under Sources in the manager to load the helpers from its
dashboard.

The full source build can drive the same install through FTP. See
[Operations](docs/OPERATIONS.md) for addresses, helper order and recovery.

## Build from source

```sh
make check   # host tests and documentation checks, no console
make build   # browser UI, native title and helpers
make release # local archive from the generated artifacts
```

`make build` needs the host tools in [Build](docs/BUILD.md). It writes the title
to `build/EVO-PLAYER-PS5-*/output/app/PPSA99997/` and the helpers to
`build/*.elf`.

## Controls

- D-pad moves focus. X activates the focused item.
- Circle stops playback that started from Nuvio and returns to browsing.
- Player settings opens the native EVO interface. Playback started there keeps
  EVO's own stop confirmation.

## Limits

- Firmware 13.60 only. The permission helper refuses other firmware.
- The UI server must run for the whole session. The app loads its interface from
  it.
- Software AV1 through dav1d is not in this build. Other codecs, subtitles and
  long sessions still need testing.
- The jailbreak clears on reboot. Start the loader, FTP and ShadowMount again,
  then push one permission watcher for the new boot.

## Documentation

| Task | Guide |
|---|---|
| Install, start or update Nuvio | [Operations](docs/OPERATIONS.md) |
| Build the port | [Build](docs/BUILD.md) |
| Understand the browser and native player | [Architecture](docs/ARCHITECTURE.md) |
| Check what the console tests establish | [Validation](docs/VALIDATION.md) |
| Cut a release | [Release](docs/RELEASE.md) |
| Diagnose a failure or restore files | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| Change code or documentation | [Contributing](docs/CONTRIBUTING.md) |
| Find a term or source | [Glossary](docs/GLOSSARY.md), [Sources](docs/SOURCES.md) |

## Contribute

Fresh-boot testing, playback return checks, subtitles and longer playback
sessions all help. Send the firmware, the artifact hashes and the expected and
observed behavior. Remove account details and private stream URLs from reports.
See [Contributing](docs/CONTRIBUTING.md).

## Licences

Project code and patches use GPL-3.0-or-later. See [LICENSE](LICENSE) and
[Sources](docs/SOURCES.md). The build creates its runtime from independently
authored source in EVO and does not extract Sony modules from the console. Keep
account state, addon URLs and console logs outside source control.
