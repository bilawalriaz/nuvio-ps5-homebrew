# Announcement notes

How to describe Nuvio PS5 and where to announce it.

## Describe the project

Call it a community Nuvio TV integration with EVO native playback on a
jailbroken PS5. Credit NuvioMedia for the UI and the EVO contributors for the
player and the browser bridge.

This port adds macOS builds, focused controller input, provider seeking, Nuvio
branding, playback exit and route restoration. It adds no decoder, no exploit
and no support for other firmware.

## Before you announce

1. Run `make check` and read the final diff.
2. Check every reachable Git revision for private state and restricted files.
3. Check the artwork attribution and the retained license notices.
4. Confirm the release assets and their hashes.
5. Record a short console demo with the tested artifact.
6. Read the [Release](RELEASE.md) rules for distribution.

The file scanner covers tracked and unignored files. Review account identifiers,
LAN addresses, signed URLs and logs by hand, and keep private receipts and raw
hardware logs out of the repository.

An announcement keeps the alpha status and the open tests. The package carries
the integration source, not every upstream archive, so do not call it a complete
corresponding-source bundle.

## Demonstration plan

Use the generated test addon and clip in [Operations](OPERATIONS.md).

Record startup, D-pad focus, playback, seeking, one Circle press and the
restored page. Show the generated tone, and pause and resume during the test.
Keep account QR codes, addon URLs and private settings out of the recording.
Record real console footage.

## Hacker News notes

[Hacker News guidelines](https://news.ycombinator.com/newsguidelines.html) ask
for your own words, so write the submission and the replies yourself. These
notes only supply the facts.

[Show HN guidance](https://news.ycombinator.com/showhn.html) asks for something
people can try. A hardware project can include a video, and this one has a
release to download.

Points to cover:

- Why you wanted Nuvio on your PS5.
- The upstream UI and player work you reused.
- How the app recreates the browser around native playback.
- The rejected provider seek and what it did to the playback state machine.
- The loopback bind permission that file access did not grant.
- One tested firmware, macOS builds and a self-contained console UI server.
- The open limits and the help you want.

Do not ask for votes or coordinate comments.

## Reddit draft

Destination: r/ps5homebrew. Read its rules again before you post. The
[release rule](https://www.reddit.com/r/ps5homebrew/about/rules.json) asks for a
file scan link or other verification. Ask the moderators first when you cannot
confirm a release, and never upload private files to a scanning service.

> Title: Nuvio PS5: Nuvio TV with EVO native playback on firmware 13.60
>
> I built a community Nuvio TV integration for my jailbroken PS5. It uses
> Nuvio's account, catalogue and addon UI with EVO Player's browser bridge and
> native playback engine. Credit to NuvioMedia and the EVO contributors for
> those foundations.
>
> My changes cover macOS builds, controller focus, provider seeking, Nuvio
> branding and playback return behavior. On my 13.60 console I confirmed QR
> login, addon sync, playback and seeking that resumes. The latest exit fix logs
> decoder stop and browser reopening.
>
> This is an alpha. It needs a jailbreak each boot, a loader, FTP and
> ShadowMount, and one payload pushed per boot. The console serves its own UI, so
> no computer has to stay on. Native builds need macOS. The payload accepts
> firmware 13.60 only. Pause, subtitles, fresh-boot behavior and long sessions
> still need testing.
>
> Downloads and build instructions:
> https://github.com/bilawalriaz/nuvio-ps5-homebrew
>
> Firmware-specific testing and reproducible bug reports help. Keep account
> details and private stream URLs out of reports.
