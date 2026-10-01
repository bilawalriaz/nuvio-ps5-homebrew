#!/usr/bin/env python3
"""Check source inputs and tracked/unignored files; never contact a console."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
def main():
    pins=json.loads((ROOT/'deps.lock').read_text())
    for pin in pins['artifacts']:
        assert re.fullmatch('[0-9a-f]{64}',pin['sha256']),pin['id']
        assert 'latest' not in pin['url']
        if pin.get('commit'):assert re.fullmatch('[0-9a-f]{40}',pin['commit'])
    for required in ('README.md','LICENSE','docs/ARCHITECTURE.md','docs/VALIDATION.md','docs/RELEASE.md','assets/nuvio.rml','patches/evo.patch','patches/nuvio.patch'):
        assert (ROOT/required).is_file(),required
    proc=subprocess.run(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT,capture_output=True)
    files=[ROOT/p.decode() for p in proc.stdout.split(b'\0') if p] if proc.returncode==0 else [p for p in ROOT.rglob('*') if p.is_file() and not any(x in p.relative_to(ROOT).parts for x in ('build','.cache','.git','__pycache__','release','config'))]
    private=re.compile(rb'(?:sb_secret_[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+)')
    for p in files:
        assert p.suffix.lower() not in ('.elf','.bin','.prx','.sprx','.self','.env','.wgt'),f'Restricted artifact: {p.name}'
        assert not private.search(p.read_bytes()),f'Potential credential: {p.name}'
    print('Source pins, required files and private-artifact checks passed')
if __name__=='__main__':main()
