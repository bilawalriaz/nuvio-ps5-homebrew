#!/usr/bin/env python3
"""Package only receipt-verified generated distribution files, without settings."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import zipfile
import subprocess
from build import ROOT,WORK,TITLE,digest
from elfcheck import validate

def main():
    version=(ROOT/'VERSION').read_text().strip()
    if any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789.-' for c in version):raise RuntimeError('Invalid version')
    receipt=json.loads((WORK/'build.json').read_text())
    if receipt['title_id']!=TITLE:raise RuntimeError('Wrong title')
    pins=json.loads((ROOT/'deps.lock').read_text())
    pin=next(p for p in pins['artifacts'] if p['id']=='evo-player-nuvio-source')
    dist=WORK/pin['directory']/'output/app'/TITLE
    inventory=[]
    for name,want in receipt['files'].items():
        rel=PurePosixPath(name);p=(dist/name).resolve()
        if rel.is_absolute() or '..' in rel.parts or not p.is_relative_to(dist.resolve()) or digest(p)!=want:raise RuntimeError('App receipt mismatch')
        inventory.append((p,'app/'+TITLE+'/'+name))
    expected={f'control-{i}.elf' for i in (1,2,3,4)}|{'promote.elf','permission-watcher.elf'}
    if set(receipt['helpers'])!=expected:raise RuntimeError('Unexpected helpers')
    for name in sorted(expected):
        p=WORK/name
        if digest(p)!=receipt['helpers'][name]:raise RuntimeError('Helper receipt mismatch')
        validate(str(p));inventory.append((p,'helpers/'+name))
    ui=WORK/'ui'
    for p in sorted(ui.rglob('*')):
        if p.is_file():
            if p.is_symlink() or p.suffix.lower() not in ('.html','.js','.css','.json','.png','.jpg','.jpeg','.svg','.webp','.ico','.woff','.woff2','.ttf','.map','.txt','.md','.license','.xml','.wasm'):
                raise RuntimeError('Unexpected UI artifact: '+p.name)
            inventory.append((p,'ui/'+str(p.relative_to(ui))))
    # Include the integration's complete source alongside the binary alpha.
    tracked=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT)
    for name in tracked.decode().split('\0'):
        if name:inventory.append((ROOT/name,'source/'+name))
    out=ROOT/'release';out.mkdir(exist_ok=True)
    target=out/f'nuvio-ps5-{version}.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p,name in inventory:z.write(p,name)
        z.writestr('build.json',json.dumps(receipt,indent=2)+'\n')
        z.writestr('MANIFEST.sha256',''.join(digest(p)+'  '+name+'\n' for p,name in inventory))
    (out/'SHA256SUMS').write_text(digest(target)+'  '+target.name+'\n')
    print('Private alpha package:',target,'sha256',digest(target))
if __name__=='__main__':main()
