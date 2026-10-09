#!/usr/bin/env python3
"""Close the fixed Nuvio title and verify that its folder is unmounted."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import time
from build import WORK, ROOT, TITLE
from install import helper


def main(host=None):
    host = host or os.environ.get('PS5_HOST')
    if not host:
        raise RuntimeError('Set PS5_HOST to the configured console address')
    receipt = json.loads((WORK/'build.json').read_text())
    payload = WORK/'close.elf'
    if receipt.get('title_id') != TITLE:
        raise RuntimeError('Close helper receipt title mismatch')
    for name in ('close.elf', 'control-2.elf'):
        expected = receipt.get('helpers', {}).get(name)
        if not expected or hashlib.sha256((WORK/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Close helper receipt mismatch: ' + name)
    env = dict(os.environ)
    env['PS5_READ_IDLE_TIMEOUT'] = '8'
    result = subprocess.run(['python3', str(ROOT/'scripts/upload.py'), '--file', str(payload)],
                            env=env, capture_output=True, text=True, timeout=60)
    if result.returncode or not any(line in result.stdout.splitlines() for line in (
            'NUVIO close: process exited', 'NUVIO close: no matching process')):
        raise RuntimeError('Nuvio close did not return process evidence')
    for _ in range(10):
        with contextlib.redirect_stdout(io.StringIO()):
            response = helper(2, host)
        records = [json.loads(line) for line in response.splitlines() if line.startswith('{')]
        info = records[-1] if records else {}
        if info.get('title_id') == TITLE and info.get('mounted') is False:
            print('Nuvio closed; title unmounted')
            return 0
        time.sleep(0.5)
    raise RuntimeError('Nuvio process closed, but title remains mounted')


if __name__ == '__main__':
    raise SystemExit(main())
