#!/usr/bin/env python3
"""Report or apply upstream revision changes for the pins in deps.lock.

Host only. This script reads GitHub release and commit metadata and rewrites
`deps.lock`; it never contacts a console and never builds.

Default is a read-only drift report. `--apply` downloads and hashes each changed
input before it writes the new pin, then prints the derived files that still
name the old revision.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
API = 'https://api.github.com'
TARBALL = 'https://codeload.github.com/{repo}/tar.gz/{commit}'

# How each pinned input names a fixed upstream revision. `release-source` tracks
# the newest stable release and pins its commit; `branch-source` tracks a branch
# head; `release-asset` pins one release asset by hash.
UPSTREAMS = {
    'nuvio-tv-source': {
        'repo': 'NuvioMedia/NuvioTVSmart', 'mode': 'release-source',
        'version_key': 'release', 'directory': 'NuvioTVSmart-{commit}',
        'cache_file': 'nuvio-tv-source-{version}.tar.gz'},
    'evo-player-nuvio-source': {
        'repo': 'sainsaji/EVO-PLAYER-PS5', 'mode': 'branch-source',
        'branch': 'main', 'directory': 'EVO-PLAYER-PS5-{commit}',
        'cache_file': 'evo-player-nuvio-source-{version}.tar.gz'},
    'nuvio-official-tv-config': {
        'repo': 'NuvioMedia/NuvioTVSmart', 'mode': 'release-asset',
        'asset': 'NuvioTV-Tizen-{tag}.wgt', 'version_key': 'version',
        'cache_file': 'NuvioTV-Tizen-{version}.wgt'},
    'ps5-payload-sdk-prebuilt': {
        'repo': 'ps5-payload-dev/sdk', 'mode': 'release-asset',
        'asset': 'ps5-payload-sdk.zip', 'version_key': 'tag',
        'cache_file': 'sdk-{version}.zip'},
    'nuvio-pacbrew': {
        'repo': 'ps5-payload-dev/pacbrew-repo', 'mode': 'release-asset',
        'asset': 'ps5-payload-dev.tar.gz', 'version_key': 'tag',
        'cache_file': 'pacbrew-{version}.tar.gz'},
    'nuvio-klogsrv': {
        'repo': 'ps5-payload-dev/klogsrv', 'mode': 'release-asset',
        'asset': 'klogsrv-ps5.elf', 'version_key': 'version',
        'cache_file': 'klogsrv-ps5.elf'},
}


def get_json(url):
    request = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def download(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def latest_release(repo):
    return get_json(f'{API}/repos/{repo}/releases/latest')


def branch_commit(repo, branch):
    return get_json(f'{API}/repos/{repo}/commits/{branch}')['sha']


def tag_commit(repo, tag):
    return get_json(f'{API}/repos/{repo}/commits/{tag}')['sha']


def resolve(pin, spec, fetch=None):
    """Return the newest pin fields for one input, or None when it is current.

    `fetch` replaces network access; it maps a URL to parsed JSON, or to bytes
    when `binary` is true.
    """
    def call(url):
        if fetch is not None:
            return fetch(url)
        return get_json(url)

    def blob(url):
        if fetch is not None:
            return fetch(url, binary=True)
        return download(url)

    asset = None
    if spec['mode'] == 'branch-source':
        commit = call(f'{API}/repos/{spec["repo"]}/commits/{spec["branch"]}')['sha']
        if commit == pin.get('commit'):
            return None
        version = commit[:12]
        url = TARBALL.format(repo=spec['repo'], commit=commit)
    elif spec['mode'] == 'release-source':
        version = call(f'{API}/repos/{spec["repo"]}/releases/latest')['tag_name']
        if version == pin.get('release'):
            return None
        commit = call(f'{API}/repos/{spec["repo"]}/commits/{version}')['sha']
        url = TARBALL.format(repo=spec['repo'], commit=commit)
    else:
        release = call(f'{API}/repos/{spec["repo"]}/releases/latest')
        version = release['tag_name']
        if version == pin.get(spec['version_key']):
            return None
        name = spec['asset'].format(tag=version)
        asset = next((a for a in release['assets'] if a['name'] == name), None)
        if asset is None:
            raise RuntimeError(f'{pin["id"]}: release {version} has no asset {name}')
        url = asset['browser_download_url']

    data = blob(url)
    fields = {'url': url, 'sha256': digest(data), 'size_bytes': len(data),
              'cache_file': spec['cache_file'].format(version=version),
              'retrieved': datetime.date.today().isoformat()}
    if spec['mode'] == 'release-asset':
        fields[spec['version_key']] = version
        if asset.get('digest') == 'sha256:' + fields['sha256']:
            fields['evidence'] = '[SOURCE-VERIFIED] GitHub reports this asset digest and a local download reproduced it.'
        else:
            fields['evidence'] = '[LOCALLY RECORDED] sha256 computed from the version-pinned download; no upstream checksum.'
    else:
        fields['commit'] = commit
        fields['directory'] = spec['directory'].format(commit=commit, version=version)
        if spec['mode'] == 'release-source':
            fields['release'] = version
        fields['evidence'] = '[SOURCE-VERIFIED] Inspected pinned source; checksum recorded locally. Not firmware validation.'
    return fields


def stale_references(values):
    """Name the tracked files that still cite a replaced revision."""
    hits = []
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or path.suffix not in ('.md', '.py', '.patch', '.json', '.txt'):
            continue
        if any(part in ('build', '.cache', '.git', '__pycache__', 'release') for part in path.relative_to(ROOT).parts):
            continue
        if path.name == 'update_upstreams.py' or path.name == 'deps.lock':
            continue
        text = path.read_text(errors='ignore')
        if any(v and v in text for v in values):
            hits.append(str(path.relative_to(ROOT)))
    return hits


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply', action='store_true', help='rewrite deps.lock for drifted inputs')
    ap.add_argument('--only', action='append', default=[], help='restrict to these pin ids')
    args = ap.parse_args()

    document = json.loads((ROOT/'deps.lock').read_text())
    changed = []
    drift = 0
    for pin in document['artifacts']:
        spec = UPSTREAMS.get(pin['id'])
        if not spec or (args.only and pin['id'] not in args.only):
            continue
        current = pin.get('commit') or pin.get(spec['version_key'], '')
        updated = resolve(pin, spec)
        if updated is None:
            print(f'{pin["id"]}: current ({current[:12]})')
            continue
        drift += 1
        newest = updated.get('commit') or updated.get(spec['version_key'], '')
        print(f'{pin["id"]}: {current[:12]} -> {newest[:12]}' if updated.get('commit')
              else f'{pin["id"]}: {current} -> {newest}')
        if args.apply:
            previous = [pin.get('commit'), pin.get(spec['version_key'])]
            pin.update(updated)
            changed.append((pin['id'], previous))

    if not drift:
        print('deps.lock is at the newest upstream revision for every tracked pin')
        return 0
    if not args.apply:
        print(f'{drift} input(s) drifted; re-run with --apply to update deps.lock')
        return 0

    document['generated'] = datetime.date.today().isoformat()
    (ROOT/'deps.lock').write_text(json.dumps(document, indent=2) + '\n')
    for pin_id, previous in changed:
        hits = stale_references([v for v in previous if v])
        print(f'{pin_id}: updated; recheck derived files: ' + (', '.join(hits) if hits else 'none'))
    print('Next: run `make check`, then `make build`, then re-run the console validation.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
