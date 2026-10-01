# Build

## Prepare the host

The native build adapter requires macOS.
Install Xcode command-line tools before building.
Install the required host tools separately.
The builder does not install or update them.

| Tool | Recorded version | Purpose |
|---|---|---|
| Python | 3.13.7 | Build scripts, tests and file checks |
| Node.js | 22.23.2 | Nuvio UI build and JavaScript tests |
| LLVM and lld | 23.1.2 | PS5 compilation and linking |
| Homebrew coreutils | Version not recorded | GNU tools for the upstream build |
| Apple command-line tools | Version not recorded | macOS converter and SDK paths |
| FFmpeg | Version not recorded | Optional generated test clip |

Python 3.12 is the minimum stated in `deps.lock`.
The recorded host test uses Python 3.13.7.
A different host version needs a new build record.
FFmpeg on the computer only creates the test clip.
EVO uses separate target libraries inside the console.

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

The adapter selects LLVM through Homebrew.
It locates `ld.lld` through `PATH` before setting the build environment.
Keep the required lld executable accessible through `PATH`.

## Build the title

1. Open a terminal at the repository root.
2. Run the host checks.
3. Run the full build.
4. Save the resulting receipt with the artifacts.

```sh
make check
make build
mkdir -p config
cp build/build.json config/candidate-build.json
```

The build verifies each archive against `deps.lock` before extraction.
It uses `npm ci` with the upstream lock file.
It applies source changes through checked anchors.
It stops if a required anchor changes.

The builder generates `patches/evo.patch` and `patches/nuvio.patch` for review.
The Python adapters already apply these changes.
Do not apply the generated patches again.

The native builder records generated file hashes in `build/build.json`.
A build receipt identifies artifacts.
It does not certify console execution.
The builder leaves `firmware_validation` as `[UNKNOWN]`.

## Find the output

| Path | Contents |
|---|---|
| `build/ui/` | Browser UI and public runtime configuration |
| `build/EVO-PLAYER-PS5-21524a4a6effa65312be2026042e44a96efca4c6/output/app/PPSA99997/` | Native folder title |
| `build/control-1.elf` | Registration helper |
| `build/control-2.elf` | Title information helper |
| `build/control-3.elf` | Launch helper |
| `build/control-4.elf` | Staged runtime hash helper |
| `build/permission-watcher.elf` | Resident Nuvio permission helper |
| `build/promote.elf` | One-time Nuvio permission helper |
| `build/build.json` | Native file, helper and input hashes |
| `.cache/` | Verified input archives |

The title includes the generated `sce_module/libc.prx` runtime.
Keep ELF section headers intact.
Do not strip helper ELFs.

## Build only the UI

```sh
make ui
```

This command builds `build/ui` without building the native title.
It does not create a new native receipt.
Keep the native receipt for the installed title.
UI changes still need browser tests on the console.

## Change generated directories

The builder supports two environment variables:

```sh
export NUVIO_WORK_DIR="/absolute/path/to/dedicated-build-directory"
export NUVIO_CACHE_DIR="/absolute/path/to/dedicated-cache-directory"
```

Use a dedicated directory for each variable.
The builder removes existing extracted source directories before rebuilding.
Use the same values for the build, server, install and update scripts.
Do not place unrelated files in those source directories.

## Public browser configuration

The source build lacks the official TV login configuration.
The builder reads that configuration from the pinned Nuvio Tizen 1.2.1 package.
It accepts an anonymous or publishable browser key.
It checks the configured service URLs for HTTPS.
It copies only the selected browser configuration values.
It does not install Tizen executables.

The generated UI contains this public configuration.
Keep `build/` outside Git.
Do not substitute a Supabase service key.
