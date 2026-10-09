# Getting started

Nuvio PS5 runs the Nuvio TV interface and plays video through EVO's native engine.
The single-install build includes the interface and its startup helper.

## Before you install

Use a PS5 on firmware 13.60. Run your jailbreak for the current boot.
Start ShadowMount and an ELF loader on port 9021 through your existing setup.
Start FTP and read the console's address and FTP port from that setup.

A jailbreak lets homebrew run until the console restarts.
ShadowMount adds the installed app folder to the PS5 home screen.
The ELF loader starts the permission helper bundled inside Nuvio.

## Install the app

1. Download the single-install `PPSA99997.zip` release asset.
2. Unpack it on your computer.
3. Open an FTP client and connect to the PS5's address and FTP port.
4. Copy the `PPSA99997` folder into `/data/homebrew/`.
5. Refresh ShadowMount's homebrew list.
6. Open the Nuvio tile after registration finishes.

Check the folder layout:

```text
/data/homebrew/PPSA99997/
  eboot.bin
  sce_module/
  sce_sys/
  webui/
```

Nuvio serves its interface from the PS5. You can disconnect your computer after installation.
Sign in through Nuvio's account screen and configure your addons.

## Use the controller

Use the D-pad to move focus and X to select.
During playback, use the player controls to pause or seek.
Press Circle to stop a Nuvio video and return to browsing.
Player settings opens EVO's native settings.

## After a reboot

Run your jailbreak again and start ShadowMount and the ELF loader.
Open Nuvio from its tile. The app loads its bundled helper automatically.

## Update Nuvio

Close Nuvio before replacing its files.
Copy the new release's `PPSA99997` folder over the old folder through FTP.
Keep `/data/nuvio/`, which stores your settings and browser state.
Open Nuvio after the copy finishes.

Release 0.1.0-alpha.2 needs the older `nuvio.elf` boot payload.
Use the single-install release notes to identify the new version.

## If something fails

- No tile: check the folder path and refresh ShadowMount.
- Opening Nuvio or a browser connection error: check the current boot's jailbreak and ELF loader on port 9021.
- Missing interface: check that the installed folder includes `webui/`.
- Missing catalog, thumbnails or login QR: check the console's network and DNS settings.

For a bug report, include your firmware, Nuvio version, loader, visible error,
and the action that caused it. Remove account details and stream URLs from logs.
See [Troubleshooting](TROUBLESHOOTING.md) for developer diagnostics.
