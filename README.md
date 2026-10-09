# Nuvio PS5

<img src="assets/logo.png" width="190" alt="Nuvio">

Nuvio PS5 runs Nuvio TV on a jailbroken PlayStation 5 and plays streams with EVO
Player's native engine. Nuvio supplies the account, catalogue and addon screens.
EVO supplies the controller input, audio and hardware video decoding.

This is a community project with no connection to Sony, NuvioMedia or EVO Player.


## What it does

- Shows Nuvio TV in the PS5 system browser, served from the console itself.
- Hands a stream to the native engine for hardware decoding.
- Reopens the browser on your last Nuvio page when playback stops.
- Moves browser focus with the D-pad, so X activates the item you selected.

## Start here

You need a PS5 on firmware **13.60**, jailbroken for the current boot, with
ShadowMount and an ELF loader listening on port **9021**. Keep the console on 13.60.

The new single-install build includes its permission helper and browser UI.
Open Nuvio from its home-screen tile. The app loads the helper automatically.
After a reboot, run your jailbreak again before opening Nuvio.

1. Download `PPSA99997.zip` for the single-install version and unpack it.
2. Start FTP on the PS5 and note its address and port.
3. Connect with an FTP client, then copy `PPSA99997` into `/data/homebrew/`.
4. Refresh ShadowMount's homebrew list and wait for the Nuvio tile.
5. Open Nuvio. Sign in or configure your addons, then choose something to watch.

The final path must be `/data/homebrew/PPSA99997/eboot.bin`, with `webui/`
and `sce_sys/` beside it. Avoid an extra nested `PPSA99997` folder.
See [the beginner guide](docs/GETTING_STARTED.md) for updates and troubleshooting.

Release `0.1.0-alpha.2` needed a separate `nuvio.elf` startup payload. In
`v0.1.0-alpha.4`, `PPSA99997.zip` includes the permission helper and the title
starts it automatically. You do not need to transfer a separate `nuvio.elf`.
The current boot still needs the jailbreak, ShadowMount and the ELF loader on
port 9021.

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

## Requirements and codec support

- Firmware 13.60, ShadowMount and the current boot's ELF loader on port 9021.
- Use FTP for manual installation and updates.
- Software AV1 through dav1d is not included.
- To build from source, install macOS host tools: Xcode command-line tools, Homebrew LLVM and Node.js.

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
