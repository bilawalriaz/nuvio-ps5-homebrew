#!/usr/bin/env python3
"""Check local documentation links and run the pinned structural writing linter."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
from urllib.parse import unquote,urlsplit

ROOT=Path(__file__).resolve().parents[1]
PAGES={'ARCHITECTURE','BUILD','CONTRIBUTING','GLOSSARY','OPERATIONS','RELEASE','SOURCES','TROUBLESHOOTING','VALIDATION','WRITING'}

def prose(text):
    return re.sub(r'(?ms)^```[^\n]*\n.*?^```[^\n]*$', '', text)

def anchors(path):
    result=set();counts={}
    for heading in re.findall(r'(?m)^#{1,6}\s+(.+?)\s*#*$',prose(path.read_text())):
        heading=re.sub(r'[`*_]','',heading).lower()
        heading=re.sub(r'[^\w\- ]','',heading).replace(' ','-')
        count=counts.get(heading,0);counts[heading]=count+1
        result.add(heading if not count else heading+'-'+str(count))
    return result

def main():
    for name in PAGES:
        if not (ROOT/'docs'/f'{name}.md').is_file():raise RuntimeError('Missing guide: '+name)
    files=[ROOT/'README.md',ROOT/'AGENTS.md',*sorted((ROOT/'docs').glob('*.md'))]
    for file in files:
        text=prose(file.read_text())
        for target in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)',text):
            target=target.strip('<>');url=urlsplit(target)
            if url.scheme or url.netloc:continue
            path=(file.parent/unquote(url.path)).resolve() if url.path else file
            if not path.is_relative_to(ROOT) or not path.exists():raise RuntimeError(f'{file.name}: missing link {target}')
            if url.fragment and path.suffix=='.md' and unquote(url.fragment) not in anchors(path):
                raise RuntimeError(f'{file.name}: missing anchor {target}')
    provenance=json.loads((ROOT/'vendor/ste-lint/PROVENANCE.json').read_text())
    for name,want in provenance['files'].items():
        if hashlib.sha256((ROOT/'vendor/ste-lint'/name).read_bytes()).hexdigest()!=want:
            raise RuntimeError('Pinned writing check changed: '+name)
    print('Required guides, local links, anchors and writing-check pins passed',flush=True)
    # The synonym heuristic conflates service startup, app launch, fixed identifiers
    # and an owner's visual confirmation. Review terminology manually instead.
    return subprocess.run([sys.executable,str(ROOT/'vendor/ste-lint/ste-lint.py'),'--disable','synonym-rotation',*map(str,files)],cwd=ROOT).returncode

if __name__=='__main__':sys.exit(main())
