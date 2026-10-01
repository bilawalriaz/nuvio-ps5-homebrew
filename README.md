# Nuvio PS5 Homebrew

Nuvio PS5 combines Nuvio TV 1.2.1 with EVO Player's native PS5 playback engine.
Nuvio provides the account, catalogue and addon interface.
EVO provides controller input, audio and hardware video decoding.

This community project is independent of Sony, NuvioMedia and EVO Player.
The current version is `0.1.0-alpha.1`.
This is an experimental source alpha for homebrew developers.
Public launch preparation is in [Launch](docs/LAUNCH.md).
This public repository distributes source only.
Prebuilt binaries are not available.

## Requirements and limits

- A retail PS5 on firmware 13.60, jailbroken for the current boot.
- A configured ELF loader, etaHEN FTP and ShadowMount.
- A macOS computer to build the native title.
- A computer serving the UI on the LAN throughout use.

This is a folder homebrew title, not a retail installable package.
Unmodified consoles cannot run it.
Other firmware is untested and the permission helper refuses it.
The UI server is required even after installation.

## Tested target

The test console is a retail PS5 on firmware 13.60.
The console needs an active jailbreak for each boot.
The permission helper refuses other firmware.
Do not update the console firmware.

The owner confirmed QR login, addon sync, controller focus, media playback and resumed seeking.
The console logs show native H.264 decoding and successful seeks.
Nuvio-branded startup also has owner confirmation.
The corrected playback exit stops the decoder and reopens the browser in the console log.
The owner has not yet confirmed the visible page after that correction.
See [validation](docs/VALIDATION.md) for exact artifact hashes and test limits.

## Start here

| Task | Guide |
|---|---|
| Prepare the computer and build the port | [Build](docs/BUILD.md) |
| Install, start or update Nuvio | [Operations](docs/OPERATIONS.md) |
| Diagnose a failure or restore files | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| Understand the browser and native player | [Architecture](docs/ARCHITECTURE.md) |
| Check what the console tests establish | [Validation](docs/VALIDATION.md) |
| Prepare a release | [Release](docs/RELEASE.md) |
| Change code or documentation | [Contributing](docs/CONTRIBUTING.md) |
| Find a term or source | [Glossary](docs/GLOSSARY.md), [sources](docs/SOURCES.md) |

## Get the source

```sh
git clone https://github.com/bilawalriaz/nuvio-ps5-homebrew.git
cd nuvio-ps5-homebrew
make check
```

Read [Build](docs/BUILD.md) for native build prerequisites.
Read [Operations](docs/OPERATIONS.md) before installing or uploading helpers.

## Host checks and builds

Run these commands from the repository root:

```sh
make check
make build
```

`make check` tests host code and documentation without contacting a console.
`make build` builds the browser UI, native title and fixed-purpose helpers on macOS.
`make ui` builds only the browser UI.
`make release` creates a local archive from the generated artifacts.
See the guides before running console commands.

## How playback works

Keep the UI server running on a computer that the PS5 can reach.
The system browser displays Nuvio through the title's local proxy.
The browser closes when a stream starts in the native player.
The title opens the browser again after playback stops.
Nuvio loading artwork covers automatic transitions.
The console may still display its own browser transitions.

Circle stops playback started from Nuvio.
Player settings opens the native EVO interface.
Playback started there retains EVO's stop confirmation.
Software AV1 through dav1d is absent from this build.
Other codecs, subtitles and long sessions need further tests.

## Contribute

Useful contributions include fresh-boot testing, playback return checks, subtitles and longer playback sessions.
Include firmware, artifact hashes and expected versus observed behavior in a report.
Remove account information and private stream URLs.
See [Contributing](docs/CONTRIBUTING.md).

## Licenses

Project code and patches use GPL-3.0-or-later.
See [LICENSE](LICENSE) and [source attribution](docs/SOURCES.md).
The build creates its runtime from independently authored source in EVO.
It does not extract Sony modules from the console.
Keep account state, addon URLs and console logs outside source control.
