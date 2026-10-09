#!/usr/bin/env python3
"""Verify the installed Nuvio artifact, launch it and report fresh startup events."""
import argparse
import contextlib
import ftplib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import time

from build import WORK, TITLE
from install import helper
from update import parse_eboot_report

LOG_PATH = '/data/nuvio/evo.log'
LOG_LIMIT = 8 * 1024 * 1024
# Extract complete events, never the rest of a line: logs also hold private URLs.
EVENT = re.compile(
    r'\b(?:BUILD [A-Za-z0-9_.-]{1,128}(?![A-Za-z0-9_.-])|'
    r'server: socket (?:ok fd=\d+|failed errno=\d+)|'
    r'server: bind (?:ok 127\.0\.0\.1:\d+|failed port=\d+ errno=\d+)|'
    r'server: listen (?:ok port=\d+|failed port=\d+ errno=\d+)|'
    r'server: connection accepted|'
    r'bootstrap: promotion requested|'
    r'bootstrap: promotion failed stage=[a-z-]{1,32} errno=\d+|'
    r'bootstrap: promotion (?:verified|failed) errno=\d+|'
    r'title-ui: packaged assets selected|'
    r'title-ui: response status=\d{3}|'
    r'page: route [A-Za-z][A-Za-z0-9_-]{0,63}(?![A-Za-z0-9_-]))')


def fresh_bytes(before, after):
    """Accept appended bytes; reject rotation rather than treating old logs as new."""
    if not after.startswith(before):
        raise RuntimeError('Console log changed its prefix; retry with a fresh baseline')
    return after[len(before):]


def startup_events(data):
    # A partial final line may grow on the next poll. Process complete lines only.
    complete = data.rsplit(b'\n', 1)[0] if b'\n' in data else b''
    return [match.group() for match in EVENT.finditer(complete.decode('utf8', errors='replace'))]


def classify(events, gate, title_ui=False, auto_bootstrap=False):
    if any(e.startswith('bootstrap: promotion failed ') for e in events):
        return 'bootstrap_failed'
    if any('failed errno=' in e or ('failed port=' in e) for e in events):
        return 'listener_failed'
    built = any(e.startswith('BUILD ') for e in events)
    bound = any(e.startswith('server: bind ok ') for e in events)
    listening = any(e.startswith('server: listen ok ') for e in events)
    accepted = 'server: connection accepted' in events
    routed = any(e.startswith('page: route ') for e in events)
    bootstrapped = not auto_bootstrap or 'bootstrap: promotion verified errno=0' in events
    if bootstrapped and built and bound and listening and accepted and (gate == 'loopback' or (routed and (not title_ui or
            ('title-ui: packaged assets selected' in events and
             'title-ui: response status=200' in events)))):
        return 'loopback_ready' if gate == 'loopback' else 'ui_route_observed'
    return 'waiting_for_fresh_startup'


def read_log(ftp):
    data = bytearray()

    def receive(block):
        if len(data) + len(block) > LOG_LIMIT:
            raise RuntimeError('Console log exceeds the 8 MiB feedback limit')
        data.extend(block)

    try:
        ftp.retrbinary('RETR ' + LOG_PATH, receive)
    except ftplib.error_perm as exc:
        # Only an explicit missing-file response is an empty baseline.
        if str(exc).startswith('550') and not data:
            return b''
        raise
    return bytes(data)


def verify_helpers(receipt, directory):
    for action in (2, 3, 5):
        name = f'control-{action}.elf'
        expected = receipt.get('helpers', {}).get(name)
        path = directory / name
        if not expected or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Helper receipt mismatch: ' + name)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--host', default=os.environ.get('PS5_HOST'))
    ap.add_argument('--ftp-port', type=int, default=int(os.environ.get('PS5_FTP_PORT', '0')))
    ap.add_argument('--receipt', type=Path, default=WORK / 'build.json')
    ap.add_argument('--expected-eboot-sha256', help='Override the expected installed eboot for a recorded diagnostic')
    ap.add_argument('--gate', choices=('ui', 'loopback'), default='ui')
    ap.add_argument('--wait', type=float, default=30, help='Startup observation window in seconds (1 to 60)')
    args = ap.parse_args()
    if not args.host or not 0 < args.ftp_port < 65536:
        ap.error('Supply the console host and FTP port')
    if not 1 <= args.wait <= 60:
        ap.error('--wait must be between 1 and 60 seconds')
    receipt = json.loads(args.receipt.read_text())
    if receipt.get('title_id') != TITLE:
        ap.error('Receipt title must be ' + TITLE)
    expected = args.expected_eboot_sha256 or receipt.get('files', {}).get('eboot.bin', '')
    if not re.fullmatch('[0-9a-f]{64}', expected):
        ap.error('Expected eboot must be a SHA-256 hex digest')
    verify_helpers(receipt, WORK)
    if 'close.elf' in receipt.get('helpers', {}):
        import close
        close.main(args.host)
    with contextlib.redirect_stdout(io.StringIO()):
        info_text = helper(2, args.host)
    responses = [json.loads(line) for line in info_text.splitlines() if line.startswith('{')]
    info = responses[-1] if responses else {}
    if (info.get('title_id') != TITLE or info.get('installed') is not True or
            info.get('mounted') is not False or info.get('source_type') != 'folder'):
        raise RuntimeError('Close Nuvio; feedback needs an installed, unmounted folder title')
    with contextlib.redirect_stdout(io.StringIO()):
        hashes = parse_eboot_report(helper(5, args.host))
    if hashes['installed'][1] != expected:
        raise RuntimeError('Installed eboot differs from the expected artifact; launch skipped')
    print('Installed eboot sha256=' + expected, flush=True)
    with ftplib.FTP() as ftp:
        ftp.connect(args.host, args.ftp_port, timeout=10)
        ftp.login(os.environ.get('PS5_FTP_USER', 'anonymous'), os.environ.get('PS5_FTP_PASS', 'anonymous'))
        before = read_log(ftp)
        with contextlib.redirect_stdout(io.StringIO()):
            helper(3, args.host)
        print('Launch accepted; observing fresh startup events', flush=True)
        deadline = time.monotonic() + args.wait
        seen = []
        while time.monotonic() < deadline:
            events = startup_events(fresh_bytes(before, read_log(ftp)))
            if events[:len(seen)] != seen:
                raise RuntimeError('Fresh startup events changed; retry the observation')
            for event in events[len(seen):]:
                print(event, flush=True)
            seen = events
            status = classify(events, args.gate, receipt.get('ui_hosting') == 'title',
                              bool(receipt.get('automatic_bootstrap')))
            if status != 'waiting_for_fresh_startup':
                print('Feedback: ' + status)
                return 0 if status in ('loopback_ready', 'ui_route_observed') else 1
            time.sleep(min(1, max(0, deadline - time.monotonic())))
        print('Feedback: no complete fresh startup result within the observation window')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
