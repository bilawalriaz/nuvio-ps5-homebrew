#!/usr/bin/env python3
"""Update a closed, unmounted Nuvio title and import its private synced addons."""
import argparse
import ftplib
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import urllib.parse
from build import WORK, ROOT, TITLE
from install import helper


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--host',default=os.environ.get('PS5_HOST'))
    ap.add_argument('--ftp-port',type=int,default=int(os.environ.get('PS5_FTP_PORT','0')))
    ap.add_argument('--previous-receipt',type=Path,required=True)
    ap.add_argument('--sync-addons',action='store_true')
    ap.add_argument('--test-addon',help='Explicit LAN test manifest URL')
    args=ap.parse_args()
    if not args.host or not 0<args.ftp_port<65536: ap.error('Supply console host and FTP port')
    old=json.loads(args.previous_receipt.read_text());new=json.loads((WORK/'build.json').read_text())
    if old['title_id']!=TITLE or new['title_id']!=TITLE or not old['files'].keys()<=new['files'].keys():
        raise RuntimeError('Receipt identity/inventory mismatch')
    pin=next(p for p in json.loads((ROOT/'deps.lock').read_text())['artifacts'] if p['id']=='evo-player-nuvio-source')
    dist=WORK/pin['directory']/'output/app'/TITLE
    changed=[]
    for name,want in new['files'].items():
        rel=PurePosixPath(name);p=(dist/name).resolve()
        if rel.is_absolute() or '..' in rel.parts or not p.is_relative_to(dist.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=want:
            raise RuntimeError('Local receipt mismatch')
        if want!=old['files'].get(name): changed.append(name)
    allowed={'eboot.bin','sce_sys/icon0.png','sce_sys/pic0.png','sce_sys/pic1.png','assets/rml/nuvio.rml','assets/icons/nuvio-wordmark.png'}
    # The browser UI now ships inside the title folder and is served from the
    # console by the boot payload, so a UI update replaces webui/ as one unit.
    if any(n not in allowed and not n.startswith('webui/') for n in changed):
        raise RuntimeError('Changes exceed reviewed native/UI asset allowlist')
    info_text=helper(2,args.host)
    lines=[l for l in info_text.splitlines() if l.startswith('{')]
    info=json.loads(lines[-1]) if lines else {}
    if info.get('title_id')!=TITLE or not info.get('installed') or info.get('mounted') is not False or info.get('source_type')!='folder':
        raise RuntimeError('Refusing update: title must be installed as an unmounted folder')
    with ftplib.FTP() as ftp:
        ftp.connect(args.host,args.ftp_port,timeout=15);ftp.login(os.environ.get('PS5_FTP_USER','anonymous'),os.environ.get('PS5_FTP_PASS','anonymous'));ftp.voidcmd('TYPE I')
        def read(path):
            out=io.BytesIO();ftp.retrbinary('RETR '+path,out.write);return out.getvalue()
        def write(path,data):
            temp=path+'.nuvio-update'
            try: ftp.size(temp)
            except ftplib.error_perm as exc:
                if not str(exc).startswith('550'):raise
            else:raise RuntimeError('Staging path already exists')
            ftp.storbinary('STOR '+temp,io.BytesIO(data))
            if hashlib.sha256(read(temp)).digest()!=hashlib.sha256(data).digest():raise RuntimeError('Console staging verification failed')
            ftp.rename(temp,path)
        if args.sync_addons:
            conf=read('/data/nuvio/nuvio.conf').decode()
            fields=dict(line.split('=',1) for line in conf.splitlines() if '=' in line)
            host=fields['host'];port=int(fields['port'])
            if '/' in host or '..' in host:raise RuntimeError('Invalid stored UI host')
            store_path=f'/data/nuvio/webui/{host}_{port}.json'
            original=read(store_path);store=json.loads(original)
            profile=str(json.loads(store.get('activeProfileId','"1"')))
            envelope=json.loads(store.get('installedAddonUrls','[]'))
            urls=envelope['profiles'].get(profile,[]) if isinstance(envelope,dict) else envelope
            if not isinstance(urls,list) or any(not isinstance(u,str) for u in urls):raise RuntimeError('Invalid synced addon list')
            urls=list(dict.fromkeys(u.rstrip('/') if not u.endswith('/manifest.json') else u for u in urls))
            if args.test_addon and args.test_addon not in urls:urls.append(args.test_addon)
            manifests=[u if u.endswith('/manifest.json') else u+'/manifest.json' for u in urls]
            if len(manifests)>12 or any(len(u.encode())>=512 or urllib.parse.urlsplit(u).scheme not in ('http','https') for u in manifests):
                raise RuntimeError('Synced addons exceed native provider limits')
            # Private backup stays on the console; never print addon URLs/tokens.
            backup='/data/nuvio/webui/backup-'+hashlib.sha256(original).hexdigest()+'.json'
            ftp.storbinary('STOR '+backup,io.BytesIO(original))
            if args.test_addon:
                if isinstance(envelope,dict):envelope['profiles'][profile]=urls
                else:envelope=urls
                store['installedAddonUrls']=json.dumps(envelope)
                write(store_path,json.dumps(store).encode())
            config=json.dumps({'addons':manifests}).encode()
            write('/data/nuvio/addons.json',config)
            # Also configure an existing standalone EVO settings root when present.
            try:ftp.cwd('/data/evoplayer')
            except ftplib.error_perm as exc:
                if not str(exc).startswith('550'):raise
            else:
                try:
                    existing=read('/data/evoplayer/addons.json');prior=json.loads(existing).get('addons',[])
                except ftplib.error_perm as exc:
                    if not str(exc).startswith('550'):raise
                    existing=b'';prior=[]
                combined=list(dict.fromkeys(prior+manifests))
                if len(combined)>12:raise RuntimeError('Standalone EVO addon count exceeds limit')
                if existing:ftp.storbinary('STOR /data/evoplayer/addons-before-nuvio.json',io.BytesIO(existing))
                write('/data/evoplayer/addons.json',json.dumps({'addons':combined}).encode())
                print('Configured existing standalone EVO addon settings')
            print('Synced native addons:',len(manifests),'(URLs kept private)')
        # Check every installed predecessor before mutating any app file.
        originals={}
        for name in changed:
            remote='/data/homebrew/'+TITLE+'/'+name
            try:before=read(remote)
            except ftplib.error_perm as exc:
                if not str(exc).startswith('550') or name in old['files']:raise
                before=None
            if name in old['files']:
                if before is None or hashlib.sha256(before).hexdigest()!=old['files'][name]:raise RuntimeError('Installed predecessor mismatch: '+name)
            elif before is not None:raise RuntimeError('Unexpected pre-existing asset: '+name)
            originals[name]=before
        for name in changed:
            remote='/data/homebrew/'+TITLE+'/'+name
            before=originals[name]
            if before is not None:
                backup='/data/homebrew/ps5-homebrew-dev/nuvio-'+hashlib.sha256(before).hexdigest()+'-'+name.replace('/','_')
                ftp.storbinary('STOR '+backup,io.BytesIO(before))
                if hashlib.sha256(read(backup)).digest()!=hashlib.sha256(before).digest():raise RuntimeError('Backup verification failed')
            write(remote,(dist/name).read_bytes())
            if name=='eboot.bin':ftp.sendcmd('SITE CHMOD 755 '+remote)
            print('Verified and replaced',name,'sha256',new['files'][name])
    print('Closed-title update complete; launch separately')


if __name__=='__main__':main()
