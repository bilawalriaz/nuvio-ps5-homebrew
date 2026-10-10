# Sources

## Pinned build inputs

`deps.lock` records download URLs, archive hashes, retrieval dates and license
notes. The builder checks each hash before it extracts the archive. The hashes
identify locally recorded downloads and are not maintainer signatures.

| Input | Fixed identity | Use |
|---|---|---|
| [Nuvio TV](https://github.com/NuvioMedia/NuvioTVSmart/tree/25b984f778e4083dc6c2e768fdb5fcf46012e8b7) | `25b984f778e4083dc6c2e768fdb5fcf46012e8b7`, version 1.2.3 | Browser UI and official branding |
| [EVO Player](https://github.com/sainsaji/EVO-PLAYER-PS5/tree/9ee9a5420c73b5be448610e5f0a90a29a75592f3) | `9ee9a5420c73b5be448610e5f0a90a29a75592f3` | Native title, bridge, decoder and runtime source |
| [Unofficial Stremio PS5 port](https://github.com/Sp9nky/unofficial-stremio-ps5-port/tree/a4b12fb515a3044f073f4befba0dd90d8244eddd) | `a4b12fb515a3044f073f4befba0dd90d8244eddd` | Read-only comparison of sandbox networking changes |
| [PS5 payload SDK](https://github.com/ps5-payload-dev/sdk/releases/tag/v0.43) | v0.43 | Headers, wrappers and payload link inputs |
| [pacbrew target libraries](https://github.com/ps5-payload-dev/pacbrew-repo/releases/tag/v0.39) | v0.39 | Target libraries only |
| [FFmpeg](https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz) | 7.1.1 | Target libav* libraries. The build compiles this source and installs it over the sysroot copy |
| [ps5-homebrew-ui](https://github.com/blackbearreloaded/ps5-homebrew-ui/tree/4bd942579dd981b3df9c740438489ca6a614ddc0) | `4bd942579dd981b3df9c740438489ca6a614ddc0` | EVO's UI kit. The EVO archive omits submodules, so the build installs this pinned tree into `third_party/` |
| [Official Nuvio TV package](https://github.com/NuvioMedia/NuvioTVSmart/releases/tag/1.2.3) | Tizen 1.2.3 | Selected public browser login configuration |
| [klogsrv](https://github.com/ps5-payload-dev/klogsrv/releases/tag/v0.9) | v0.9 | Optional diagnostics used in the console session |

The native build takes the SDK from v0.43 and does not use the older host
toolchain from pacbrew. The pacbrew selection supplies only the target homebrew
library prefix. The dav1d archive is absent from that selection, and the adapter
omits the unused link input. The build compiles the FFmpeg 7.1.1 source with
EVO's minimal configuration and installs it over the sysroot copy, replacing
the pacbrew libav* libraries. The build omits libdav1d, so software AV1
remains unsupported. The GPL-3.0 `ps5-homebrew-ui` kit unpacks under
`third_party/` from its own pinned archive during the build.

## Source attribution

Project code and patches use GPL-3.0-or-later unless a file states otherwise.
NuvioMedia owns the upstream Nuvio code and branding. The EVO contributors own
their native implementation and boilerplate. The SDK FreeBSD headers and target
libraries carry their own license terms. Keep those terms when you distribute a
build.

`vendor/control.c` comes from the development workspace's Aurora control helper.
Its header credits the launch ABI source and the ShadowMount API references. The
builder changes its title and labels to Nuvio before it compiles the file. The
retained SHA-256 sources keep their original notices. The runtime comes from
independently authored source inside the pinned EVO input.

The writing checks copy the MIT-licensed STE linter at the revision below. Its
license stays in `vendor/ste-lint/LICENSE`.

The Stremio source pin is a comparison reference. Nuvio does not copy its
`console_curl.c` or `posix_fixes.c` code.

| Writing reference | Revision |
|---|---|
| [ASD-STE100 skill](https://github.com/danyuchn/asd-ste100-skill/tree/7d4a135a199a5d7447c4886bcd7ffe742a627bc9) | `7d4a135a199a5d7447c4886bcd7ffe742a627bc9` |
| [Humanizer](https://github.com/blader/humanizer/tree/225a6f39ac85f76ee48dbad772ea4abe4ed6c9d8) | `225a6f39ac85f76ee48dbad772ea4abe4ed6c9d8` |

Writing reference retrieval date: 2026-10-01. See [Writing](WRITING.md) for their
scope and limits.

## Distribution

The [PS5 Homebrew Store catalog](https://github.com/blackbearreloaded/ps5-homebrew-catalog)
pins one release asset per title. [Release](RELEASE.md) describes the store
record.

## Signing implementation reference

[SOURCE-VERIFIED] Retrieved on 2026-10-09:
[kstuff FSELF authentication handling](https://github.com/EchoStretch/kstuff/blob/d44a25400ecfab7e31afe9eb2c7c7c99770e8f56/ps5-kstuff/uelf/fself.c).
`is_header_fself` reads the embedded 136-byte authentication record.
`try_handle_fself_trap` uses it when present, otherwise selecting a default profile.
This is an inspected reference revision, not the console's resident build identity.

The experimental signing profile comes from `samples/install_app/Makefile` in
the checksum-pinned SDK v0.43 archive. The port uses no kstuff source code.

## Hardware source

[Validation](VALIDATION.md) records the portable console evidence. The original
session record stays in the private development workspace. Raw console logs and
private settings are not publication inputs. Use filtered excerpts with exact
artifact identities.
