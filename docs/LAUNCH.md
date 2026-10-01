# Public launch preparation

Prepared on 2026-10-01 for an experimental source alpha.
The owner authorized a separate public source repository.
This repository has no binary release.

## Position the project

Describe the project as a community Nuvio TV integration with EVO native playback on a jailbroken PS5.
Credit NuvioMedia for the UI and EVO contributors for the player and existing browser bridge.
Describe this port's work: macOS builds, focused input, provider seeking, branding, playback exit and route restoration.
Do not claim a new decoder, exploit or universal firmware support.

[TESTED-ON-CONSOLE] Baseline account login, addon sync, playback and resumed seeking have owner observations.
[TESTED-ON-CONSOLE] Branded startup has owner confirmation.
[TESTED-ON-CONSOLE] The corrected exit artifact logs decoder closure and browser reopening.
[UNKNOWN] Its visible restored route still needs confirmation.
See [Validation](VALIDATION.md) for exact hashes and the remaining acceptance tests.

## Source announcement checklist

1. Run `make check` and review the final diff.
2. Review every reachable Git revision for private state and restricted artifacts.
3. Review artwork attribution and retained license notices.
4. Commit the reviewed source and documentation.
5. Push the commit to the repository.
6. Publish the approved source snapshot to the separate public repository.
7. Open the public repository while signed out.
8. Check README links and the source build instructions.
9. Confirm this public repository has no binary release.
10. Record a short console demo with the exact tested artifact.

The current file scanner checks tracked and unignored working files.
It does not establish that every historical blob is free of private information.
Review account identifiers, LAN addresses, signed URLs and logs separately.
Do not publish private build receipts or the development workspace's raw hardware logs.

A source announcement must retain the alpha status and pending hardware checks.
Public binary distribution also requires the gates in [Release](RELEASE.md#before-public-binary-distribution).
The current package includes integration source, but not every upstream source archive.
Do not describe that archive as a complete corresponding-source bundle.

## Preparation checks

[LOCALLY BUILT] Eight host regressions passed on 2026-10-01.
Local documentation links, writing checks, source pins and private-artifact checks passed.
Writing checks retain advisory findings, with no hard failures.
A pattern scan covered 63 historical blobs reachable from local Git refs.
It found no matching credential patterns or restricted artifact extensions.
This limited scan does not certify the absence of every private identifier.
No native rebuild or console test ran during this documentation change.

## Demonstration plan

Use the generated test addon and clip described in [Operations](OPERATIONS.md).
Record startup, D-pad focus, playback, seeking, one Circle press and the restored page.
Confirm the generated tone, pause and resume during the test.
Keep account QR codes, addon URLs and private settings outside the recording.
Record actual console footage rather than a mockup.
Add the demo link to the README after reviewing the recording.
No public demo has been prepared in this change.

## Hacker News author notes

[Hacker News guidelines](https://news.ycombinator.com/newsguidelines.html) prohibit generated or AI-edited posts and comments.
Write your submission and discussion replies yourself.
These notes supply facts for your own explanation, not submission prose.

[Show HN guidance](https://news.ycombinator.com/showhn.html) asks for something people can try.
Hardware projects can include a video or detailed article.
Use a public source link and an actual console demo to explain the hardware barrier.
If the project cannot be tried, use a regular submission instead.

Points to cover in your own words:

- Why you wanted Nuvio on your PS5.
- The upstream UI and player contributions.
- Browser recreation around native playback.
- The provider seek rejection and its state-machine consequence.
- File access succeeding while loopback bind lacked permission.
- One tested firmware, macOS builds and the required LAN UI server.
- Exact alpha limitations and the contribution you want help with.

Do not solicit votes or coordinate comments.
Posting guidance was checked on 2026-10-01.

## Reddit draft

Suggested destination: r/ps5homebrew.
Review its rules again immediately before posting.
The [release rule](https://www.reddit.com/r/ps5homebrew/about/rules.json) requests file scan links or other verification.
If verification is unavailable, ask moderators before posting a release.
Do not upload private artifacts to a scanning service.
No scan or moderator contact was performed in this change.

Use this draft only after the source repository is publicly accessible:

> Title: Nuvio PS5 source alpha: Nuvio TV with EVO native playback on firmware 13.60
>
> I have been working on a community Nuvio TV integration for my jailbroken PS5.
> It uses Nuvio's account/catalogue/addon UI and EVO Player's existing browser bridge and native playback engine.
> Credit goes to NuvioMedia and EVO contributors for those foundations.
>
> My changes cover macOS builds, controller focus, provider seeking, Nuvio branding and playback return behavior.
> On my 13.60 console, I confirmed QR login, addon sync, playback and seeking that resumes.
> The latest exit fix logs decoder stop and browser reopening.
> Visible route acceptance is still pending.
>
> This is an experimental source alpha.
> It needs a jailbreak each boot, loader/FTP/ShadowMount services and a computer serving the UI throughout use.
> Native builds currently require macOS.
> The permission helper refuses firmware other than 13.60.
> Pause, subtitles, fresh-boot behavior and longer sessions still need acceptance tests.
>
> Source and build instructions: https://github.com/bilawalriaz/nuvio-ps5-homebrew
> Prebuilt binaries are unavailable while acceptance and source-distribution review remain pending.
> Firmware-specific testing and reproducible bug reports would help.
> Please keep account information and private stream URLs out of reports.

Add reviewed demo and verification links only when they exist.
This draft does not claim a scan or a public binary download.
Reddit rules were checked on 2026-10-01.
