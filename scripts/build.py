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


def sdk_install_auth_profile(makefile):
    """Read the public SDK install_app sample's exact signing metadata."""
    joined = makefile.replace('\\\n', ' ')
    authority = re.findall(r'^AUTHID\s*:=\s*(0x[0-9A-Fa-f]+)\s*$', joined, re.MULTILINE)
    info = re.findall(r'^AUTHINFO\s*:=\s*([0-9A-Fa-f \t]+)$', joined, re.MULTILINE)
    if len(authority) != 1 or len(info) != 1:
        raise RuntimeError('Pinned SDK signing profile declarations changed')
    values = info[0].split()
    if len(values) != 0x88 or any(not re.fullmatch('[0-9A-Fa-f]{2}', value) for value in values):
        raise RuntimeError('SDK authentication info must contain exactly 136 bytes')
    if not 0 <= int(authority[0], 16) <= 0xffffffffffffffff:
        raise RuntimeError('SDK authority exceeds its 64-bit field')
    return {'authority': authority[0], 'auth_info': ''.join(values).lower()}


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


def instrument_loopback_server(source):
    """Log proxy socket, bind, listen and browser accept as separate results."""
    replacements = (
        ('    int fd = socket(AF_INET, SOCK_STREAM, 0);\n'
         '    if (fd < 0) { LOG("server: socket errno=%d", errno); return; }',
         '    int fd = socket(AF_INET, SOCK_STREAM, 0);\n'
         '    if (fd < 0) { LOG("server: socket failed errno=%d", errno); return; }\n'
         '    LOG("server: socket ok fd=%d", fd);'),
        ('    if (bind(fd, (struct sockaddr *)&a, sizeof a) != 0 || listen(fd, 16) != 0) {\n'
         '        LOG("server: bind/listen 127.0.0.1:%d failed errno=%d", s_port, errno);\n'
         '        close(fd);\n'
         '        return;\n'
         '    }',
         '    if (bind(fd, (struct sockaddr *)&a, sizeof a) != 0) {\n'
         '        int error = errno;\n'
         '        LOG("server: bind failed port=%d errno=%d", s_port, error);\n'
         '        close(fd);\n'
         '        return;\n'
         '    }\n'
         '    LOG("server: bind ok 127.0.0.1:%d", s_port);\n'
         '    if (listen(fd, 16) != 0) {\n'
         '        int error = errno;\n'
         '        LOG("server: listen failed port=%d errno=%d", s_port, error);\n'
         '        close(fd);\n'
         '        return;\n'
         '    }\n'
         '    LOG("server: listen ok port=%d", s_port);'),
        ('        int c = accept(s_listen_fd, NULL, NULL);\n'
         '        if (c >= 0 && s_srv_stop) { close(c); break; }',
         '        int c = accept(s_listen_fd, NULL, NULL);\n'
         '        if (c >= 0 && s_srv_stop) { close(c); break; }\n'
         '        if (c >= 0) LOG("server: connection accepted");'),
    )
    for old, new in replacements:
        if source.count(old) != 1:
            raise RuntimeError('Pinned EVO loopback server anchor changed')
        source = source.replace(old, new)
    return source


def bypass_loopback_origin_preflight(source):
    """Open EVO's browser so it can probe the local proxy without its UI server."""
    old = '''        if (s_check_rc < 0) {
            char m[256];
'''
    # adapt() inserts this only for a diagnostic build. A preprocessor guard
    # would also need a compiler definition; the earlier guard had none and
    # silently left the missing-server preflight active.
    new = '''        if (s_check_rc < 0) {
            LOG("preflight bypassed for unpromoted loopback diagnostic");
            s_check_rc = 1;
        }
        if (s_check_rc < 0) {
            char m[256];
'''
    if source.count(old) != 1:
        raise RuntimeError('Pinned EVO preflight anchor changed')
    return source.replace(old, new)


def title_ui_sources(web, provider):
    """Serve the packaged page on EVO's existing listener for the Nuvio profile."""
    replacements = (
        ('#include "evo_webui.h"', '#include "evo_webui.h"\n#include "local_ui.h"'),
        ('        else\n            proxy_request(fd, req, got, hl, method, path);',
         '''        else if (!strcmp(s_hook_profile, "nuvio")) {
            char tag[96];
            size_t tag_len = is_html_entry(path) ? hook_tag(tag, sizeof tag) : 0;
            int status = nuvio_local_ui_send(fd,
                "/data/homebrew/PPSA99997/webui", method, path, tag, tag_len);
            LOG("title-ui: response status=%d", status);
        } else
            proxy_request(fd, req, got, hl, method, path);'''),
        ('    s_check_rc = 0;\n    pthread_t t;',
         '''    /* Packaged Nuvio files need no second HTTP process. Keep the
     * configured origin as the browser-storage key for existing profiles. */
    if (!strcmp(s_hook_profile, "nuvio")) {
        s_check_rc = 1;
        s_state = P_CHECK;
        s_frames = 0;
        LOG("title-ui: packaged assets selected");
        return 0;
    }
    s_check_rc = 0;
    pthread_t t;'''),
    )
    for old, new in replacements:
        if web.count(old) != 1:
            raise RuntimeError('Pinned title-local UI anchor changed')
        web = web.replace(old, new)
    # Fresh installations must be configured before any external helper runs.
    old = "    g_host[0] = '\\0';\n    g_port = NUVIO_DEFAULT_PORT;"
    if provider.count(old) != 1:
        raise RuntimeError('Pinned Nuvio provider initialization changed')
    provider = provider.replace(old, '    snprintf(g_host, sizeof g_host, "127.0.0.1");\n    g_port = 4173;')
    return web, provider


def adapt(evo, loopback_diagnostic=False, title_ui=False, auto_bootstrap=False):
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
    web = app/'src/evo_webui.c'
    web_source = instrument_loopback_server(web.read_text())
    if loopback_diagnostic:
        web_source = bypass_loopback_origin_preflight(web_source)
    if title_ui:
        provider = app/'addons/src/provider_nuvio.c'
        web_source, provider_source = title_ui_sources(web_source, provider.read_text())
        provider.write_text(provider_source)
        for name in ('local_ui.c', 'local_ui.h'):
            shutil.copyfile(ROOT/'scripts'/name, app/'src'/name)
        # Reuse the payload server's path and MIME helpers. Its listener is
        # never called by the title; requests use EVO's existing connection.
        shutil.copyfile(ROOT/'scripts/ui_server.c', app/'src/nuvio_ui_files.c')
        replace_once(app/'Makefile',
                     'C_SRCS := $(PP_SRCS) $(UI_SRCS) $(MEDIA_SRCS) $(ADDON_SRCS)',
                     'C_SRCS := $(PP_SRCS) $(UI_SRCS) $(MEDIA_SRCS) $(ADDON_SRCS) src/local_ui.c src/nuvio_ui_files.c')
    if auto_bootstrap:
        web_source = web_source.replace('#include "evo_webui.h"', '#include "evo_webui.h"\n#include "bootstrap.h"')
        anchor = '    if (s_listen_fd >= 0) return;\n    int fd = socket(AF_INET, SOCK_STREAM, 0);'
        if web_source.count(anchor) != 1:
            raise RuntimeError('Pinned server bootstrap anchor changed')
        web_source = web_source.replace(anchor, '''    if (s_listen_fd >= 0) return;
    if (!strcmp(s_hook_profile, "nuvio")) {
        LOG("bootstrap: promotion requested");
        int rc = nuvio_bootstrap();
        if (rc == 0) LOG("bootstrap: promotion verified errno=0");
        else LOG("bootstrap: promotion failed stage=%s errno=%d", nuvio_bootstrap_stage(), errno);
        if (rc != 0) return;
    }
    int fd = socket(AF_INET, SOCK_STREAM, 0);''')
        for name in ('bootstrap.c', 'bootstrap.h'):
            shutil.copyfile(ROOT/'scripts'/name, app/'src'/name)
        replace_once(app/'Makefile', 'src/local_ui.c src/nuvio_ui_files.c',
                     'src/local_ui.c src/nuvio_ui_files.c src/bootstrap.c')
    web.write_text(web_source)
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

    The stylesheet stays a plain render-blocking <link>. A `media="print"`
    link switched to `all` on load paints earlier, but the console's browser
    then renders Nuvio unstyled, so the pattern is not usable here.
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
    ap.add_argument('--auto-bootstrap', type=int, metavar='LOADER_PORT',
                    help='Embed promotion helper and submit it to the specified loopback loader port')
    ap.add_argument('--auth-profile', choices=('default', 'sdk-install-app'), default='default',
                    help='Signing metadata for a controlled permission test')
    ap.add_argument('--title-ui', action='store_true',
                    help='Serve packaged UI files inside the title for a single-install test')
    args = ap.parse_args()
    if args.auto_bootstrap is not None and (not args.title_ui or not 1 <= args.auto_bootstrap <= 65535):
        ap.error('--auto-bootstrap requires --title-ui and a valid loader port')
    loopback_diagnostic = os.environ.get('NUVIO_UNPROMOTED_LOOPBACK_DIAGNOSTIC') == '1'
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
    adapt(evo, loopback_diagnostic=loopback_diagnostic, title_ui=args.title_ui, auto_bootstrap=args.auto_bootstrap is not None)
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
    bootstrap_metadata = None
    if args.auto_bootstrap is not None:
        payload = WORK/'bootstrap-promote.elf'
        run([sdk/'bin/prospero-clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
             ROOT/'scripts/promote.c', '-lkernel_sys', '-lkernel_web', '-o', payload], env=env)
        import elfcheck
        elfcheck.validate(str(payload))
        raw = payload.read_bytes()
        if len(raw) > 1048576:
            raise RuntimeError('Bootstrap ELF exceeds the transfer bound')
        blob = evo/'projects/evoplayer/src/nuvio_bootstrap_blob.h'
        blob.write_text('#define NUVIO_BOOTSTRAP_PORT '+str(args.auto_bootstrap)+'\n'+
                        'static const unsigned char nuvio_bootstrap_elf[] = {\n'+
                        ',\n'.join(','.join('0x'+raw[i:i+16][j:j+1].hex() for j in range(len(raw[i:i+16])))
                                    for i in range(0,len(raw),16))+'\n};\n')
        bootstrap_metadata = {'loader_port': args.auto_bootstrap, 'payload_sha256': digest(payload),
                              'payload_bytes': len(raw)}
    # The app link expands "${PS5_SYSROOT}/lib"/*.so and relies on libkernel.so
    # coming before libkernel_web.so: with --as-needed the first stub that
    # satisfies a symbol is the one recorded in DT_NEEDED, and the module
    # imports exactly that library. A UTF-8 collation puts libkernel.so last,
    # so the title imported libkernel_web.prx and never started on the console.
    # C collation restores libkernel.prx. Do not remove this.
    env['LC_ALL'] = 'C'
    run(['bash', evo/'scripts/package-app.sh'], cwd=evo, env=env)
    auth_profile = None
    if args.auth_profile == 'sdk-install-app':
        # This is metadata from a pinned public example, not inferred capability
        # bits. Hardware must establish whether the resident HEN honours it.
        profile_source = sdk/'samples/install_app/Makefile'
        auth_profile = sdk_install_auth_profile(profile_source.read_text())
        tool = evo/'output/app/.build/host/ps5-native-tool'
        run([tool, 'self', '--sign', '--in', evo/'output/app/.build/eboot.elf',
             '--out', evo/'output/app'/TITLE/'eboot.bin', '--magic', '0x1D3D154F',
             '--authority', auth_profile['authority'], '--auth-info', auth_profile['auth_info']])
        run([tool, 'self', '--inspect', '--file', evo/'output/app'/TITLE/'eboot.bin'])
        auth_profile = {**auth_profile, 'source': 'SDK samples/install_app/Makefile',
                        'source_sha256': digest(profile_source)}
    # Reuse the reviewed, fixed-purpose controls with Nuvio's own identity.
    control = (ROOT/'vendor/control.c').read_text().replace('AURORA', 'NUVIO').replace('Aurora', 'Nuvio').replace('aurora', 'nuvio').replace('PPSA99998', TITLE)
    control = control.replace('../../payloads/common/sha256.h', str(ROOT/'vendor/sha256.h'))
    (WORK/'control.c').write_text(control)
    for action in (1, 2, 3, 4, 5):
        inputs = [WORK/'control.c'] + ([ROOT/'vendor/sha256.c'] if action in (4, 5) else [])
        run([sdk/'bin/prospero-clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
             '-DNUVIO_CONTROL_ACTION='+str(action), *inputs, '-lkernel_sys', '-lkernel_web',
             '-lSceUserService', '-lSceSystemService', '-o', WORK/('control-'+str(action)+'.elf')], env=env)
    run([sdk/'bin/prospero-clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
         ROOT/'scripts/close.c', '-lkernel_sys', '-lkernel_web', '-o', WORK/'close.elf'], env=env)
    run([sdk/'bin/prospero-clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
         ROOT/'scripts/promote.c', '-lkernel_sys', '-lkernel_web',
         '-o', WORK/'promote.elf'], env=env)
    # One boot payload: it grants the title its network privilege and serves the
    # browser UI from the installed title folder (scripts/ui_server.c). That is
    # why no computer has to run an HTTP server on the same network.
    run([sdk/'bin/prospero-clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
         '-DNUVIO_WATCH', ROOT/'scripts/promote.c', ROOT/'scripts/ui_server.c',
         '-lkernel_sys', '-lkernel_web', '-o', WORK/'nuvio.elf'], env=env)
    dist = evo/'output/app'/TITLE
    (dist/'portable.txt').touch()
    # The UI travels inside the title folder, so one archive installs a working
    # app and the payload serves it over loopback with no LAN origin.
    shutil.rmtree(dist/'webui', ignore_errors=True)
    shutil.copytree(WORK/'ui', dist/'webui')
    receipt = {'title_id': TITLE, 'firmware_validation': '[UNKNOWN]',
               'ui_hosting': 'title' if args.title_ui else 'boot-payload',
               'automatic_bootstrap': bootstrap_metadata, 'auth_profile': args.auth_profile, 'auth_profile_metadata': auth_profile,
               'diagnostic_mode': 'unpromoted_loopback' if loopback_diagnostic else None,
               # Explicit names, not a glob: a stale helper from an earlier
               # build in the same work directory must not enter the receipt.
               'helpers': {name: digest(WORK/name) for name in (
                   'control-1.elf', 'control-2.elf', 'control-3.elf', 'control-4.elf', 'control-5.elf',
                   'promote.elf', 'nuvio.elf', 'close.elf')},
               'source_pins': {k: fetch(k)[0]['sha256'] for k in ('nuvio-tv-source','evo-player-nuvio-source','nuvio-pacbrew','ps5-payload-sdk-prebuilt','nuvio-official-tv-config')},
               'files': {str(p.relative_to(dist)): digest(p) for p in dist.rglob('*') if p.is_file()}}
    (WORK/'build.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('Native title:', dist, '\nReceipt:', WORK/'build.json')


if __name__ == '__main__':
    main()
