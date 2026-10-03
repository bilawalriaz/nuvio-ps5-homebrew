# Build

## Get a release instead

Most users do not build anything. Download `PPSA99997.zip` from the
[latest release](https://github.com/bilawalriaz/nuvio-ps5-homebrew/releases/latest)
and follow [Operations](OPERATIONS.md). Build from source only to change the
port or to test native code.

## Prepare the host

The native build adapter needs macOS. Install the Xcode command-line tools, then
install the tools below yourself. The builder never installs or updates them.

| Tool | Recorded version | Purpose |
|---|---|---|
| Python | 3.13.7 | Build scripts, tests and file checks |
| Node.js | 22.23.2 | Nuvio UI build and JavaScript tests |
| LLVM and lld | 23.1.2 | PS5 compilation and linking |
| Homebrew coreutils | Version not recorded | GNU tools for the upstream build |
| Apple command-line tools | Version not recorded | macOS converter and SDK paths |
| FFmpeg | Version not recorded | Optional generated test clip |

```sh
brew install llvm lld coreutils
```

Install the `lld` formula as well as `llvm`. Homebrew keeps `ld.lld` outside the
LLVM prefix from LLVM 19 on, and the SDK linker wrapper reads the `lld` formula
prefix.

Python 3.12 is the minimum in `deps.lock`. The recorded host test uses Python
3.13.7. A different host version needs a new build record. FFmpeg on the computer
only creates the test clip. EVO uses its own target libraries inside the console.

Check the host tools:

```sh
python3 --version
node --version
npm --version
brew --prefix llvm
brew --prefix coreutils
command -v ld.lld
xcrun --show-sdk-path
```

The adapter selects LLVM through Homebrew and finds `ld.lld` on `PATH` before it
sets the build environment. Keep the lld executable on `PATH`.

## Build the title

1. Open a terminal at the repository root.
2. Run the host checks.
3. Run the full build.
4. Save the receipt with the artifacts.

```sh
make check
make build
mkdir -p config
cp build/build.json config/candidate-build.json
```

The build checks each archive against `deps.lock` before it unpacks it, runs
`npm ci` with the upstream lock file, and applies the source changes through
checked anchors. It stops when an anchor moves.

The builder writes `patches/evo.patch` and `patches/nuvio.patch` for review. The
Python adapters already apply those changes, so do not apply the patches again.

The builder records generated file hashes in `build/build.json`. A receipt names
artifacts. It does not certify console execution. The builder leaves
`firmware_validation` as `[UNKNOWN]`.

## Find the output

| Path | Contents |
|---|---|
| `build/ui/` | Browser UI and public runtime configuration |
| `build/EVO-PLAYER-PS5-*/output/app/PPSA99997/` | Native folder title |
| `build/control-1.elf` | Registration helper |
| `build/control-2.elf` | Title information helper |
| `build/control-3.elf` | Launch helper |
| `build/control-4.elf` | Staged runtime hash helper |
| `build/nuvio.elf` | Single boot payload: privileges and the console UI server |
| `build/promote.elf` | One-time Nuvio permission helper |
| `build/build.json` | Native file, helper and input hashes |
| `.cache/` | Checked input archives |

The title includes the generated `sce_module/libc.prx` runtime and the whole
browser UI under `webui/`. `nuvio.elf` serves that folder from the console, so it
needs no network host. Keep the ELF section headers intact and do not strip the
payload or helper ELFs. The loader reads the section headers to size each
transfer.

## Build only the UI

```sh
make ui
```

This writes `build/ui` without touching the native title or the native receipt.
Keep the native receipt for the installed title. A full `make build` copies
`build/ui` into the title as `webui/`. A UI-only build does not, so serve it with
`scripts/serve.py` while you iterate or copy it into an installed title.

## Change generated directories

The builder reads two environment variables:

```sh
export NUVIO_WORK_DIR="/absolute/path/to/dedicated-build-directory"
export NUVIO_CACHE_DIR="/absolute/path/to/dedicated-cache-directory"
```

Use a dedicated directory for each variable. The builder removes existing
extracted source directories before it rebuilds. Use the same values for the
build, server, install and update scripts.

## Public browser configuration

The source build does not carry the official TV login configuration. The builder
reads that configuration from the pinned Nuvio Tizen 1.2.2 package. It accepts an
anonymous or publishable browser key and checks the configured service URLs for
HTTPS. It copies only the selected browser configuration values and installs no
Tizen executables.

The generated UI holds this public configuration. Keep `build/` outside Git and
never substitute a Supabase service key.

## Update a pinned input

```sh
make upstream
```

`scripts/update_upstreams.py` reports which `deps.lock` pins are behind their
upstream release. `--apply` re-pins a changed input only after it downloads and
hashes the new archive, and the builder verifies those hashes as usual.

## The build pins its locale

`scripts/build.py` runs the packaging step with `LC_ALL=C`. Do not remove it. The
app link expands `${PS5_SYSROOT}/lib` with a shell glob, and with `--as-needed`
the first stub that satisfies a kernel symbol is the one recorded in the module's
import table. Under a UTF-8 collation `libkernel.so` sorts after
`libkernel_web.so`, so the title imports `libkernel_web.prx` instead of
`libkernel.prx`. Builds from 2026-10-03 did that and the console refused to start
them. The same source built under C collation imports `libkernel.prx`.
