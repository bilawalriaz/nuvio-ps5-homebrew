#!/usr/bin/env python3
"""Build the pinned Nuvio UI and an EVO-derived PS5 native title on macOS.

Host only. Generated upstream sources, modules and binaries remain outside Git.
"""
from pathlib import Path
import argparse
import base64
import re
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
import polish
import patches

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(os.environ.get('NUVIO_CACHE_DIR', str(ROOT/'.cache')))
WORK = Path(os.environ.get('NUVIO_WORK_DIR', str(ROOT/'build')))
TITLE = 'PPSA99997'  # Repository-assigned app identity, not a firmware constant.


def run(args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def lld_available():
    """prospero-lld resolves ld.lld from the LLVM prefix or the lld formula prefix."""
    if shutil.which('ld.lld'):
        return True
    try:
        prefix = subprocess.check_output(['brew', '--prefix', 'lld'], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return False
    return bool(prefix) and (Path(prefix)/'bin/ld.lld').is_file()


def fetch(key):
    pin = next(p for p in json.loads((ROOT/'deps.lock').read_text())['artifacts'] if p['id'] == key)
    p = CACHE / pin.get('cache_file', key+'.zip')
    if not p.exists():
        tmp = p.with_suffix('.download')
        try:
            with urllib.request.urlopen(pin['url'], timeout=60) as r, tmp.open('wb') as f:
                shutil.copyfileobj(r, f)
            if digest(tmp) != pin['sha256']:
                raise RuntimeError('Downloaded checksum mismatch: '+key)
            tmp.replace(p)
        finally:
            tmp.unlink(missing_ok=True)
    if digest(p) != pin['sha256']:
        raise RuntimeError('Cached checksum mismatch: '+key)
    return pin, p


def source(key):
    pin, archive = fetch(key)
    dest = WORK / pin['directory']
    if dest.exists():
        shutil.rmtree(dest)
    with tarfile.open(archive) as t:
        t.extractall(WORK, filter='data')
    return dest


def replace_once(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError('Pinned source anchor changed: '+str(path))
    path.write_text(text.replace(old, new))


def fix_provider_seek(demux, controller):
    old = '(video_stream_index < 0 && audio_stream_index < 0) ||\n        !current_media_path[0]'
    if demux.count(old) != 1:
        raise RuntimeError('Pinned provider seek guard changed')
    demux = demux.replace(old, '(video_stream_index < 0 && audio_stream_index < 0)')
    old = '    prospero_request_inplace_seek(targetSeconds, 0);\n    pp_playback_notify_seek_begin(&g_pp_pb, targetUs);'
    if controller.count(old) != 1:
        raise RuntimeError('Pinned provider seek controller changed')
    controller = controller.replace(old, '    if (prospero_request_inplace_seek(targetSeconds, 0))\n        pp_playback_notify_seek_begin(&g_pp_pb, targetUs);')
    return demux, controller


def adapt(evo):
    """Keep the native player; open its existing Nuvio bridge at startup."""
    app = evo/'projects/evoplayer'
    param_path = app/'sce_sys/param.json'
    # The published title identity and content version live in one file so the
    # store catalog can read them from a release tag.
    identity = json.loads((ROOT/'sce_sys/param.json').read_text())
    if identity['titleId'] != TITLE:
        raise RuntimeError('sce_sys/param.json titleId does not match '+TITLE)
    param = json.loads(param_path.read_text())
    param['titleId'] = identity['titleId']
    param['conceptId'] = identity['conceptId']
    param['contentId'] = identity['contentId']
    param['contentVersion'] = identity['contentVersion']
    param['localizedParameters']['en-US']['titleName'] = identity['localizedParameters']['en-US']['titleName']
    param_path.write_text(json.dumps(param, indent=2)+'\n')
    # Separate settings from an installed EVO. All persistent writes stay /data.
    for p in app.rglob('*'):
        if p.suffix in ('.c', '.h', '.cpp', '.hpp'):
            s = p.read_text()
            if '/data/evoplayer' in s or '/download0/evoplayer' in s:
                p.write_text(s.replace('/data/evoplayer', '/data/nuvio').replace('/download0/evoplayer', '/download0/nuvio'))
    replace_once(app/'core/src/Application.cpp',
                 '        evo_webui_pump();   /* #101: the system browser, when a web UI is open */',
                 '''        /* Nuvio starts once its durable settings are reachable. Existing
         * EVO code owns browser, playback handoff and shutdown lifetimes. */
        static bool nuvio_opened = false;
        if (!nuvio_opened && evo_jailbreak_is_open()) {
            const evo_provider_t *nv = evo_provider_find("nuvio");
            if (nv && nv->is_configured() &&
                evo_webui_open_ex(nv->web_ui_url(), "/", "nuvio") == 0)
                nuvio_opened = true;
        }
        evo_webui_pump();   /* #101: the system browser, when a web UI is open */''')
    replace_once(app/'src/evo_webui.c',
                 '2, 108,  0, 1812, 1080, 0x0, 0x0',
                 '2,   0,  0, 1920, 1080, 0x0, 0x0')
    # Provider sources intentionally have no local path. Check the demuxer,
    # and never announce an unqueued seek to the playback state machine.
    demux = app/'media/src/evo_demux.c'
    controller = app/'core/src/services/PlaybackController.cpp'
    fixed = fix_provider_seek(demux.read_text(), controller.read_text())
    demux.write_text(fixed[0]); controller.write_text(fixed[1])
    # Keep diagnostics available without a USB stick on this console.
    replace_once(app/'src/evo_boot_log.c', '"/mnt/usb0/evo.log"', '"/data/nuvio/evo.log"')
    # Omit the unused AV1 add-on archive from the baseline pacbrew build.
    # No stub decoder is substituted; FFmpeg's available decoders are unchanged.
    script = evo/'scripts/package-app.sh'
    s = script.read_text()
    start = s.index('    # Auto-install libdav1d into sysroot if missing')
    end = s.index('    # Static archives EVO links', start)
    s = s[:start]+s[end:]
    s = s.replace('libswscale libdav1d \\', 'libswscale \\')
    # The host converter can link macOS's zlib SDK stub. No console libc change.
    s = s.replace('eval "$("${SCRIPTS_DIR}/setup-native-app-deps.sh")"',
                  'ZLIB_INCLUDE="${NUVIO_MAC_SDK}/usr/include"\nZLIB_ARCHIVE="${NUVIO_MAC_SDK}/usr/lib/libz.tbd"')
    s = s.replace('clang++ -std=c++20', '/usr/bin/clang++ -std=c++20')
    s = s.replace('-I "${ZLIB_INCLUDE}"', '')
    s = '\n'.join('echo "Installable inventory is recorded in build.json."'
                  if line.startswith('find "${APPDIR}" -type f -printf') else line
                  for line in s.splitlines()) + '\n'
    s = s.replace('BUILD_SHA="$(git -C "${EVO}" rev-parse --short=8 HEAD 2>/dev/null || echo unknown)"',
                  'BUILD_SHA="'+fetch('evo-player-nuvio-source')[0]['commit'][:8]+'-nuvio"')
    script.write_text(s)


def patch_index(html):
    """Add the PS5 input bridge and a black first paint to Nuvio's index page.

    The PS5 browser paints its own document background before the Nuvio CSS
    applies. The white default flashes the whole screen when the browser
    reopens after playback, so the served page must be black from the first
    byte of <head>.
    """
    if html.count('<head>') != 1 or html.count('</head>') != 1:
        raise RuntimeError('Pinned UI index head anchors changed')
    if 'ps5-input.js' in html:
        raise RuntimeError('UI index already carries the PS5 bridge')
    html = html.replace('<head>',
                        '<head>\n    <style>html,body{background-color:#000;margin:0}</style>')
    return html.replace('</head>', '<script src="ps5-input.js"></script></head>')


def configure_ui(ui):
    # Official release ships the publishable browser key; never use a privileged
    # Supabase service key or copy unrelated release client settings into Git.
    _, package = fetch('nuvio-official-tv-config')
    with zipfile.ZipFile(package) as z:
        raw = z.read('nuvio.env.js').decode()
    match = re.search(r'var values = (\{.*?\});', raw, re.S)
    if not match:
        raise RuntimeError('Pinned public runtime config changed')
    official = json.loads(match[1])
    key = official.get('NUVIO_SUPABASE_ANON_KEY', '')
    if not key.startswith('sb_publishable_'):
        parts = key.split('.')
        if len(parts) != 3 or json.loads(base64.urlsafe_b64decode(parts[1]+'='*(-len(parts[1])%4))).get('role') != 'anon':
            raise RuntimeError('Release does not contain an anonymous publishable key')
    path = ui/'nuvio.env.js'
    source = path.read_text()
    for name in ('NUVIO_SUPABASE_URL', 'NUVIO_SUPABASE_ANON_KEY',
                 'NUVIO_SUPABASE_FALLBACK_URL', 'TV_LOGIN_WEB_BASE_URL',
                 'DEVICE_LOGIN_WEB_BASE_URL', 'AVATAR_PUBLIC_BASE_URL'):
        value = official.get(name, '')
        if name != 'NUVIO_SUPABASE_ANON_KEY' and value and not value.startswith('https://'):
            raise RuntimeError('Official public configuration must use HTTPS')
        source, count = re.subn(r'"'+name+r'":\s*"[^"\n]*"', lambda m: json.dumps(name)+': '+json.dumps(value), source)
        if count != 1:
            raise RuntimeError('Pinned UI runtime config anchor changed')
    path.write_text(source)
    shutil.copyfile(ROOT/'scripts/ps5-input.js', ui/'ps5-input.js')
    index = ui/'index.html'
    index.write_text(patch_index(index.read_text()))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ui-only', action='store_true')
    args = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    nv = source('nuvio-tv-source')
    polish.patch_nuvio(nv)
    run(['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=nv)
    run(['npm', 'run', 'build'], cwd=nv)
    ui = WORK/'ui'
    shutil.copytree(nv/'dist', ui, dirs_exist_ok=True)
    configure_ui(ui)
    if args.ui_only:
        print('Host UI built:', ui)
        return
    if os.uname().sysname != 'Darwin':
        raise RuntimeError('This native host adapter currently requires macOS.')
    if not lld_available():
        raise RuntimeError('ld.lld not found. Install LLVM and the lld formula: brew install llvm lld')
    sdk = WORK/'sdk/ps5-payload-sdk'
    _, sdk_zip = fetch('ps5-payload-sdk-prebuilt')
    with zipfile.ZipFile(sdk_zip) as z:
        z.extractall(WORK/'sdk')
    _, ports = fetch('nuvio-pacbrew')
    with tarfile.open(ports) as t:
        prefix = 'opt/ps5-payload-sdk/target/user/homebrew/'
        t.extractall(WORK/'ports', members=[m for m in t.getmembers() if m.name.startswith(prefix)], filter='data')
    shutil.copytree(WORK/'ports/opt/ps5-payload-sdk/target/user/homebrew', sdk/'target/user/homebrew', dirs_exist_ok=True)
    # v0.43's ZIP does not preserve executable permissions for all host wrappers.
    for p in (sdk/'bin').iterdir():
        if p.is_file():
            p.chmod(p.stat().st_mode | 0o111)
    evo = source('evo-player-nuvio-source')
    adapt(evo)
    polish.apply(evo, nv)
    patches.write_patch(fetch('evo-player-nuvio-source')[1], evo, ROOT/'patches/evo.patch')
    patches.write_patch(fetch('nuvio-tv-source')[1], nv, ROOT/'patches/nuvio.patch')
    env = os.environ.copy()
    llvm = subprocess.check_output(['brew', '--prefix', 'llvm'], text=True).strip()
    core = subprocess.check_output(['brew', '--prefix', 'coreutils'], text=True).strip()
    env.update(PS5_PAYLOAD_SDK=str(sdk), LLVM_CONFIG=llvm+'/bin/llvm-config',
               PS5_LLD=shutil.which('ld.lld') or '',
               NUVIO_MAC_SDK=subprocess.check_output(['xcrun', '--show-sdk-path'], text=True).strip())
    env['PATH'] = ':'.join([core+'/libexec/gnubin', llvm+'/bin', str(sdk/'bin'), env['PATH']])
    run(['bash', evo/'scripts/package-app.sh'], cwd=evo, env=env)
    # Reuse the reviewed, fixed-purpose controls with Nuvio's own identity.
    control = (ROOT/'vendor/control.c').read_text().replace('AURORA', 'NUVIO').replace('Aurora', 'Nuvio').replace('aurora', 'nuvio').replace('PPSA99998', TITLE)
    control = control.replace('../../payloads/common/sha256.h', str(ROOT/'vendor/sha256.h'))
    (WORK/'control.c').write_text(control)
    for action in (1, 2, 3, 4):
        inputs = [WORK/'control.c'] + ([ROOT/'vendor/sha256.c'] if action == 4 else [])
        run([sdk/'bin/prospero-clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
             '-DNUVIO_CONTROL_ACTION='+str(action), *inputs, '-lkernel_sys', '-lkernel_web',
             '-lSceUserService', '-lSceSystemService', '-o', WORK/('control-'+str(action)+'.elf')], env=env)
    for name, flags in (('promote', []), ('permission-watcher', ['-DNUVIO_WATCH'])):
        run([sdk/'bin/prospero-clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
             *flags, ROOT/'scripts/promote.c', '-lkernel_sys', '-lkernel_web',
             '-o', WORK/(name+'.elf')], env=env)
    dist = evo/'output/app'/TITLE
    (dist/'portable.txt').touch()
    receipt = {'title_id': TITLE, 'firmware_validation': '[UNKNOWN]',
               'helpers': {p.name: digest(p) for p in WORK.glob('*.elf')},
               'source_pins': {k: fetch(k)[0]['sha256'] for k in ('nuvio-tv-source','evo-player-nuvio-source','nuvio-pacbrew','ps5-payload-sdk-prebuilt','nuvio-official-tv-config')},
               'files': {str(p.relative_to(dist)): digest(p) for p in dist.rglob('*') if p.is_file()}}
    (WORK/'build.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('Native title:', dist, '\nReceipt:', WORK/'build.json')


if __name__ == '__main__':
    main()
