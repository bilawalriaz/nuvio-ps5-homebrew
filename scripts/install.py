#!/usr/bin/env python3
"""Stage and verify a first Nuvio install; refuse to overwrite an existing title."""
import argparse
import ftplib
import hashlib
import io
import json
import os
import re
from pathlib import Path, PurePosixPath
import subprocess
import urllib.parse

from build import ROOT, WORK, TITLE

# The UI is served from the console by nuvio.elf, so a first install needs no
# LAN origin. The loopback origin matches the port the payload binds and the
# value it writes into nuvio.conf when the file is absent.
DEFAULT_ORIGIN = 'http://127.0.0.1:4173'


def helper(action, host, helper_dir=WORK):
    helper_env=dict(os.environ, PS5_HOST=host)
    if action==5:
        helper_env['PS5_READ_IDLE_TIMEOUT']=str(max(
            60.0,float(helper_env.get('PS5_READ_IDLE_TIMEOUT','3'))))
    idle_timeout=float(helper_env.get('PS5_READ_IDLE_TIMEOUT','3'))
    # Upload has separate connect/send budgets. Let the uploader finish its
    # receive window before the parent interrupts a slow console hash.
    helper_timeout=10+30+max(35,idle_timeout+5)+5
    result = subprocess.run(['python3', str(ROOT/'scripts/upload.py'), '--file',
                             str(helper_dir/f'control-{action}.elf')],
                            env=helper_env,
                            capture_output=True, text=True, timeout=helper_timeout)
    print(result.stdout, end='')
    if result.returncode:
        raise RuntimeError(result.stderr or 'Control helper failed')
    # ps5ctl upload validates/transfers ELF, but its exit code is not evidence
    # that a control action ran. Require the helper's response as well.
    if action in (1, 2):
        lines = [line for line in result.stdout.splitlines() if line.startswith('{')]
        response = json.loads(lines[-1]) if lines else {}
        if response.get('status') != 0 or (action == 1 and response.get('present') is not True):
            raise RuntimeError('No successful ShadowMount response')
    elif action == 3:
        match = re.search(r'NUVIO launch_result=0x([0-9a-f]+)', result.stdout)
        if not match or int(match[1],16) & 0x80000000:
            raise RuntimeError('Native launch was refused or not confirmed')
    return result.stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--host', default=os.environ.get('PS5_HOST'))
    ap.add_argument('--ftp-port', type=int, default=int(os.environ.get('PS5_FTP_PORT', '0')))
    ap.add_argument('--origin', default=DEFAULT_ORIGIN,
                    help='UI origin stored in nuvio.conf (default: the on-console server)')
    ap.add_argument('--launch', action='store_true')
    ap.add_argument('--from-release', type=Path, metavar='DIR',
                    help='Install from an unpacked release archive instead of a source build')
    args = ap.parse_args()
    if not args.host or not args.ftp_port:
        ap.error('Set --host and --ftp-port (or PS5_HOST and PS5_FTP_PORT); no address discovery is performed.')
    origin = urllib.parse.urlsplit(args.origin)
    if origin.scheme != 'http' or not origin.hostname or origin.username or origin.password or origin.path not in ('','/') or origin.query or origin.fragment:
        ap.error('--origin must be an HTTP origin without credentials or path')
    # Provider uses a fixed 128-byte host buffer. Validate before serialization.
    if len(origin.hostname.encode()) > 127 or any(c in origin.hostname for c in '\r\n='):
        ap.error('Invalid provider host')
    if args.from_release:
        release = args.from_release.resolve()
        receipt = json.loads((release/'build.json').read_text())
        dist = release/'app'/TITLE
        helper_dir = release/'helpers'
        if not dist.is_dir() or not helper_dir.is_dir():
            raise RuntimeError('Release directory needs app/'+TITLE+' and helpers/')
    else:
        receipt = json.loads((WORK/'build.json').read_text())
        pin = next(p for p in json.loads((ROOT/'deps.lock').read_text())['artifacts'] if p['id']=='evo-player-nuvio-source')
        dist = WORK/pin['directory']/'output/app'/TITLE
        helper_dir = WORK
    if receipt['title_id'] != TITLE:
        raise RuntimeError('Build receipt title mismatch')
    # Validate the complete local receipt before opening the console connection.
    for name, expected in receipt['files'].items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise RuntimeError('Invalid receipt path')
        file = (dist/name).resolve()
        if not file.is_relative_to(dist.resolve()) or not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Local receipt mismatch: '+name)
    stage = '/data/homebrew/ps5-homebrew-dev/nuvio-stage-'+TITLE
    destination = '/data/homebrew/'+TITLE
    with ftplib.FTP() as ftp:
        ftp.connect(args.host, args.ftp_port, timeout=15)
        ftp.login(os.environ.get('PS5_FTP_USER','anonymous'), os.environ.get('PS5_FTP_PASS','anonymous'))
        ftp.voidcmd('TYPE I')
        for target in (stage, destination, destination+'.ffpfsc'):
            try:
                ftp.size(target)
            except ftplib.error_perm as exc:
                if not str(exc).startswith('550'):
                    raise
            else:
                raise RuntimeError('Refusing existing path: '+target)
            try:
                ftp.cwd(target)
            except ftplib.error_perm as exc:
                if not str(exc).startswith('550'):
                    raise
            else:
                raise RuntimeError('Refusing existing directory: '+target)
        def mkdir(path):
            # Parent existence and permission errors are distinguished with CWD.
            try:
                ftp.mkd(path)
            except ftplib.error_perm:
                ftp.cwd(path)
        for path in ('/data/homebrew','/data/homebrew/ps5-homebrew-dev',stage):
            mkdir(path)
        directories = set()
        for name, expected in receipt['files'].items():
            for parent in list(PurePosixPath(name).parents)[::-1]:
                if str(parent) != '.' and str(parent) not in directories:
                    mkdir(stage+'/'+str(parent))
                    directories.add(str(parent))
            with (dist/name).open('rb') as f:
                ftp.storbinary('STOR '+stage+'/'+name, f)
            if name == 'sce_module/libc.prx':
                continue  # etaHEN RETR tries SELF decryption; use confined helper.
            actual = hashlib.sha256()
            ftp.retrbinary('RETR '+stage+'/'+name, actual.update)
            if actual.hexdigest() != expected:
                raise RuntimeError('Staged hash mismatch: '+name)
        output = helper(4, args.host, helper_dir)
        expected = receipt['files']['sce_module/libc.prx']
        if 'sha256='+expected not in output:
            raise RuntimeError('Console runtime hash does not match receipt')
        for name in ('eboot.bin','sce_module/libc.prx'):
            ftp.sendcmd('SITE CHMOD 755 '+stage+'/'+name)
        mkdir('/data/nuvio')
        # No overwrite of pre-existing settings. First install can supply only
        # its non-secret server origin; addon/account credentials stay user-owned.
        config = '/data/nuvio/nuvio.conf'
        try:
            existing = bytearray()
            ftp.retrbinary('RETR '+config, existing.extend)
        except ftplib.error_perm as exc:
            if not str(exc).startswith('550'):
                raise
        else:
            raise RuntimeError('Existing Nuvio settings: review '+config+' before installing')
        data = f'host={origin.hostname}\nport={origin.port or 80}\nhttps=0\n'.encode()
        ftp.storbinary('STOR '+config, io.BytesIO(data))
        ftp.rename(stage, destination)
    print('Staged hashes verified; installed:', destination)
    print('Registering with ShadowMount (asynchronous):')
    helper(1, args.host, helper_dir)
    if args.launch:
        status = helper(2, args.host, helper_dir)
        compact = ''.join(status.split())
        if '"installed":true' not in compact:
            raise RuntimeError('Registration is pending. Run control-2, then control-3 when installed:true.')
        # Control-3 refuses a resident big app. Never closes an unrelated title.
        helper(3, args.host, helper_dir)
    print('Installation is not rendering or playback evidence; inspect klog and the TV.')


if __name__ == '__main__':
    main()
