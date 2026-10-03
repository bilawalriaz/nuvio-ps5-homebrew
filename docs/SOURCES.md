# Sources

## Pinned build inputs

`deps.lock` records download URLs, archive hashes, retrieval dates and license
notes. The builder checks each hash before it extracts the archive. The hashes
identify locally recorded downloads and are not maintainer signatures.

| Input | Fixed identity | Use |
|---|---|---|
| [Nuvio TV](https://github.com/NuvioMedia/NuvioTVSmart/tree/358d08cf7496b4ba04fd62a4aaaa19cab78d7aa8) | `358d08cf7496b4ba04fd62a4aaaa19cab78d7aa8`, version 1.2.2 | Browser UI and official branding |
| [EVO Player](https://github.com/sainsaji/EVO-PLAYER-PS5/tree/21524a4a6effa65312be2026042e44a96efca4c6) | `21524a4a6effa65312be2026042e44a96efca4c6` | Native title, bridge, decoder and runtime source |
| [PS5 payload SDK](https://github.com/ps5-payload-dev/sdk/releases/tag/v0.43) | v0.43 | Headers, wrappers and payload link inputs |
| [pacbrew target libraries](https://github.com/ps5-payload-dev/pacbrew-repo/releases/tag/v0.39) | v0.39 | Target libraries only |
| [Official Nuvio TV package](https://github.com/NuvioMedia/NuvioTVSmart/releases/tag/1.2.2) | Tizen 1.2.2 | Selected public browser login configuration |
| [klogsrv](https://github.com/ps5-payload-dev/klogsrv/releases/tag/v0.9) | v0.9 | Optional diagnostics used in the console session |

The native build takes the SDK from v0.43 and does not use the older host
toolchain from pacbrew. The pacbrew selection supplies only the target homebrew
library prefix. The dav1d archive is absent from that selection, and the adapter
omits the unused link input.

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

## Hardware source

[Validation](VALIDATION.md) records the portable console evidence. The original
session record stays in the private development workspace. Raw console logs and
private settings are not publication inputs. Use filtered excerpts with exact
artifact identities.
