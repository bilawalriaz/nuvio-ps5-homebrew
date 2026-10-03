#!/usr/bin/env python3
"""Package receipt-verified release assets: store zip, full archive, helpers and payloads.json.

Every artifact is checked against build/build.json before it is written. Private
settings, caches and the build source tree are never packaged.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import shutil
import zipfile
import subprocess
from build import ROOT, WORK, TITLE, digest
from elfcheck import validate

# Short descriptions for the PS5 Payload Manager source file.
HELPER_INFO = {
    'nuvio.elf': ('Nuvio',
        'Single boot payload: grants the Nuvio title its network privilege and serves the browser UI from the console. Run once per boot.'),
    'promote.elf': ('Nuvio permission promote',
        'One-time helper that grants the Nuvio title its network privileges.'),
    'control-1.elf': ('Nuvio register title',
        'Registers /data/homebrew/PPSA99997 with ShadowMount.'),
    'control-2.elf': ('Nuvio title information',
        'Reports whether the Nuvio folder title is installed and mounted.'),
    'control-3.elf': ('Nuvio launch title',
        'Launches the Nuvio folder title when it is installed and no other app runs.'),
    'control-4.elf': ('Nuvio runtime hash',
        'Hashes the staged libc.prx runtime on the console.'),
}

# Only one payload is advertised. The control and promote helpers are build and
# recovery tools; they ship inside the complete archive, not as release assets.
PUBLIC_HELPERS = ['nuvio.elf']


def helper_inventory(receipt):
    expected = {f'control-{i}.elf' for i in (1, 2, 3, 4)} | {'promote.elf', 'nuvio.elf'}
    if set(receipt['helpers']) != expected:
        raise RuntimeError('Unexpected helper inventory')
    for name in sorted(expected):
        path = WORK / name
        if digest(path) != receipt['helpers'][name]:
            raise RuntimeError('Helper receipt mismatch: ' + name)
        validate(str(path))
    return sorted(expected)


def write_store_zip(receipt, dist, target):
    """The store artifact: a zip holding the <TITLEID>/ folder at its root."""
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, want in receipt['files'].items():
            rel = PurePosixPath(name)
            path = (dist / name).resolve()
            if rel.is_absolute() or '..' in rel.parts or not path.is_relative_to(dist.resolve()):
                raise RuntimeError('App receipt path escapes the title: ' + name)
            if digest(path) != want:
                raise RuntimeError('App receipt mismatch: ' + name)
            validate_link(path)
            z.write(path, f'{TITLE}/{name}')


def validate_link(path):
    # Refuse a symlink in the store artifact: it would resolve outside the app folder.
    if path.is_symlink():
        raise RuntimeError('Refusing symlink in the title: ' + str(path))


def write_full_zip(receipt, dist, target, helpers):
    inventory = []
    for name, want in receipt['files'].items():
        rel = PurePosixPath(name)
        path = (dist / name).resolve()
        if rel.is_absolute() or '..' in rel.parts or not path.is_relative_to(dist.resolve()):
            raise RuntimeError('App receipt path escapes the title: ' + name)
        if digest(path) != want:
            raise RuntimeError('App receipt mismatch: ' + name)
        validate_link(path)
        inventory.append((path, 'app/' + TITLE + '/' + name))
    for name in helpers:
        inventory.append((WORK / name, 'helpers/' + name))
    ui = WORK / 'ui'
    for path in sorted(ui.rglob('*')):
        if path.is_file():
            if path.is_symlink() or path.suffix.lower() not in ('.html', '.js', '.css', '.json', '.png',
                    '.jpg', '.jpeg', '.svg', '.webp', '.ico', '.woff', '.woff2', '.ttf', '.map', '.txt',
                    '.md', '.license', '.xml', '.wasm'):
                raise RuntimeError('Unexpected UI artifact: ' + path.name)
            inventory.append((path, 'ui/' + str(path.relative_to(ui))))
    tracked = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT)
    for name in tracked.decode().split('\0'):
        if name:
            inventory.append((ROOT / name, 'source/' + name))
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for path, name in inventory:
            z.write(path, name)
        z.writestr('build.json', json.dumps(receipt, indent=2) + '\n')
        z.writestr('MANIFEST.sha256', ''.join(digest(path) + '  ' + name + '\n' for path, name in inventory))
    return inventory


def write_payloads_json(version, tag, repo, helpers, target):
    entries = []
    for name in helpers:
        title, description = HELPER_INFO[name]
        entries.append({
            'name': title,
            'filename': name,
            'url': f'https://github.com/{repo}/releases/download/{tag}/{name}',
            'description': description,
            'version': version,
            'category': 'Nuvio',
            'checksum': digest(WORK / name),
        })
    document = {'name': 'Nuvio PS5', 'payloads': entries}
    target.write_text(json.dumps(document, indent=2) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tag', default=None, help='Release tag used in payloads.json URLs (default v<VERSION>)')
    ap.add_argument('--repo', default='bilawalriaz/nuvio-ps5-homebrew', help='Repository for asset URLs')
    args = ap.parse_args()
    version = (ROOT / 'VERSION').read_text().strip()
    if any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789.-' for c in version):
        raise RuntimeError('Invalid version')
    tag = args.tag or 'v' + version
    receipt = json.loads((WORK / 'build.json').read_text())
    if receipt['title_id'] != TITLE:
        raise RuntimeError('Wrong title')
    pin = next(p for p in json.loads((ROOT / 'deps.lock').read_text())['artifacts'] if p['id'] == 'evo-player-nuvio-source')
    dist = WORK / pin['directory'] / 'output/app' / TITLE
    helpers = helper_inventory(receipt)
    out = ROOT / 'release'
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    assets = []
    store = out / (TITLE + '.zip')
    write_store_zip(receipt, dist, store)
    assets.append(store)
    full = out / f'nuvio-ps5-{version}.zip'
    write_full_zip(receipt, dist, full, helpers)
    assets.append(full)
    helper_dir = out / 'helpers'
    helper_dir.mkdir(exist_ok=True)
    for name in helpers:
        (helper_dir / name).write_bytes((WORK / name).read_bytes())
    # One advertised payload at the release root. The store's Payload Manager
    # source should not ask a user to choose between six helpers.
    payload_asset = out / 'nuvio.elf'
    payload_asset.write_bytes((WORK / 'nuvio.elf').read_bytes())
    assets.append(payload_asset)
    payloads = out / 'payloads.json'
    write_payloads_json(version, tag, args.repo, PUBLIC_HELPERS, payloads)
    assets.append(payloads)
    (out / 'SHA256SUMS').write_text(''.join(digest(p) + '  ' + p.name + '\n' for p in assets))
    assets.append(out / 'SHA256SUMS')
    (out / 'ASSETS').write_text(''.join(str(p.relative_to(ROOT)) + '\n' for p in assets))
    print('Store artifact:', store, digest(store))
    print('Package:', full, digest(full))
    print('Payload source:', payloads, 'tag', tag)


if __name__ == '__main__':
    main()
