#!/usr/bin/env python3
"""Update a closed, unmounted Nuvio title and import its private synced addons."""
import argparse
import ftplib
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import urllib.parse
import uuid
from build import WORK, ROOT, TITLE
from install import helper


def remote_dirs(path):
    """Parent directories of an absolute remote path, outermost first."""
    parts=path.split('/')[1:-1]
    return ['/'+'/'.join(parts[:i+1]) for i in range(len(parts))]


def ensure_remote_dirs(ftp, path):
    """Create the parent directories of an absolute remote path when missing.

    v0.12.0 adds files in new directories (assets/hui/sfx, assets/hui/fonts);
    the console FTP server refuses a STOR into a directory that does not
    exist, so each parent is created on demand."""
    for directory in remote_dirs(path):
        try:
            ftp.cwd(directory)
        except ftplib.error_perm as exc:
            if not str(exc).startswith('550'):
                raise
            ftp.mkd(directory)


def safe_param_update(before, after):
    """Allow a content-version bump and EVO's flexible-memory declaration.

    EVO v0.12.0 packages kernel.flexibleMemorySize (2 MiB..1 GiB) into the
    title metadata. Every other field must stay fixed."""
    try:
        old=json.loads(before)
        new=json.loads(after)
        old_version=old.pop('contentVersion')
        new_version=new.pop('contentVersion')
        old_parts=tuple(int(part) for part in old_version.split('.'))
        new_parts=tuple(int(part) for part in new_version.split('.'))
        old_kernel=old.pop('kernel', {})
        new_kernel=new.pop('kernel', {})
        old_memory=old_kernel.pop('flexibleMemorySize', None)
        new_memory=new_kernel.pop('flexibleMemorySize', None)
        old['kernel']=old_kernel
        new['kernel']=new_kernel
    except (TypeError, ValueError, AttributeError, KeyError):
        return False
    memory_ok=(old_memory is None and new_memory is None) or (
        isinstance(new_memory, int) and not isinstance(new_memory, bool)
        and 2097152 <= new_memory <= 1073741824 and not new_memory % 2097152
        and (old_memory is None or old_memory == new_memory))
    return (old.get('titleId')==new.get('titleId')==TITLE and
            old.get('contentId')==new.get('contentId') and
            len(old_parts)==len(new_parts)==3 and
            new_parts>=old_parts and old==new and memory_ok)


def changes_are_reviewed(changed):
    """Each changed title path must be a reviewed native or UI asset.

    The browser UI ships inside the title folder and updates as one unit
    (webui/). EVO v0.12.0 ships changed rml screens plus the UI kit's sound
    and font assets, so assets/rml/ and assets/hui/ move with the title as
    well. Everything else stays restricted to the fixed native set."""
    allowed={'eboot.bin','sce_sys/icon0.png','sce_sys/pic0.png','sce_sys/pic1.png','sce_sys/param.json','assets/rml/nuvio.rml','assets/icons/nuvio-wordmark.png'}
    prefixes=('webui/','assets/rml/','assets/hui/')
    return all(name in allowed or name.startswith(prefixes) for name in changed)


def parse_eboot_report(output):
    """Read the fixed-format on-console eboot hash helper output."""
    report={}
    for line in output.splitlines():
        match=re.fullmatch(r'NUVIO eboot (installed|backup|stage) bytes=(\d+) sha256=([0-9a-f]{64})',line)
        if match:
            report[match[1]]=(int(match[2]),match[3])
        elif line=='NUVIO eboot stage=absent':
            report['stage']=None
    if 'installed' not in report or 'backup' not in report or 'stage' not in report:
        raise RuntimeError('Console eboot helper returned incomplete evidence')
    return report


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
    if not changes_are_reviewed(changed):
        raise RuntimeError('Changes exceed reviewed native/UI asset allowlist')
    if 'close.elf' in new.get('helpers', {}):
        import close
        close.main(args.host)
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
            # The console FTP server reports SIZE as 18446744073709551615 for
            # both existing and missing paths. Use a unique staging name and
            # verify its contents before the atomic rename.
            ensure_remote_dirs(ftp,path)
            temp=path+'.nuvio-update-'+uuid.uuid4().hex
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
            if name=='eboot.bin':
                # SDK ftpsrv transforms PS5 containers on RETR. The console
                # helper below verifies the raw installed and staged bytes.
                originals[name]=None
                continue
            try:before=read(remote)
            except ftplib.error_perm as exc:
                if not str(exc).startswith('550') or name in old['files']:raise
                before=None
            if name in old['files']:
                current=hashlib.sha256(before).hexdigest() if before is not None else None
                if current not in (old['files'][name],new['files'][name]):
                    raise RuntimeError('Installed predecessor mismatch: '+name)
            elif before is not None:raise RuntimeError('Unexpected pre-existing asset: '+name)
            originals[name]=before
        if 'sce_sys/param.json' in changed and not safe_param_update(
                originals['sce_sys/param.json'], (dist/'sce_sys/param.json').read_bytes()):
            raise RuntimeError('Refusing title metadata change beyond contentVersion')
        eboot_before=None
        eboot_replace=False
        if 'eboot.bin' in changed:
            eboot_before=parse_eboot_report(helper(5,args.host))
            expected_old=old['files'].get('eboot.bin')
            expected_new=new['files'].get('eboot.bin')
            installed=eboot_before['installed'][1] if eboot_before['installed'] else None
            backup=eboot_before['backup'][1] if eboot_before['backup'] else None
            if installed==expected_new and backup==expected_new and eboot_before['stage'] is None:
                pass  # a previous run already replaced it; resume
            elif installed==expected_old and backup==expected_old and eboot_before['stage'] is None:
                eboot_replace=True
            else:
                raise RuntimeError('Console eboot or rollback backup does not match the installed receipt')
        for name in changed:
            remote='/data/homebrew/'+TITLE+'/'+name
            before=originals[name]
            if name=='eboot.bin':
                if not eboot_replace:
                    print('Already updated',name,'sha256',new['files'][name])
                    continue
                stage=remote+'.nuvio-update'
                ftp.storbinary('STOR '+stage,io.BytesIO((dist/name).read_bytes()))
                staged=parse_eboot_report(helper(5,args.host))
                if (staged['installed']!=eboot_before['installed'] or
                        staged['backup']!=eboot_before['backup'] or
                        staged['stage']!=(len((dist/name).read_bytes()),new['files'][name])):
                    raise RuntimeError('Console eboot stage hash did not match the local receipt')
                ftp.rename(stage,remote)
                ftp.sendcmd('SITE CHMOD 755 '+remote)
                installed=parse_eboot_report(helper(5,args.host))
                if (installed['installed']!=(len((dist/name).read_bytes()),new['files'][name]) or
                        installed['backup']!=installed['installed'] or installed['stage'] is not None):
                    raise RuntimeError('Installed eboot hash does not match the local receipt')
                print('Verified and replaced',name,'sha256',new['files'][name])
                continue
            if before is not None and hashlib.sha256(before).hexdigest()==new['files'][name]:
                print('Already updated',name,'sha256',new['files'][name])
                continue
            if before is not None:
                backup='/data/homebrew/ps5-homebrew-dev/nuvio-'+hashlib.sha256(before).hexdigest()+'-'+name.replace('/','_')
                ftp.storbinary('STOR '+backup,io.BytesIO(before))
                if hashlib.sha256(read(backup)).digest()!=hashlib.sha256(before).digest():raise RuntimeError('Backup verification failed')
            write(remote,(dist/name).read_bytes())
            if name=='eboot.bin':ftp.sendcmd('SITE CHMOD 755 '+remote)
            print('Verified and replaced',name,'sha256',new['files'][name])
    print('Closed-title update complete; launch separately')


if __name__=='__main__':main()
