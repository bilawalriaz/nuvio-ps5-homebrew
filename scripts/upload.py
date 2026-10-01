#!/usr/bin/env python3
"""Validate and transfer an unstripped ELF to an explicitly supplied PS5 loader."""
import argparse,hashlib,os,socket,time
from pathlib import Path
import elfcheck

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--host',default=os.environ.get('PS5_HOST'))
    ap.add_argument('--port',type=int,default=int(os.environ.get('PS5_ELF_PORT','9021')))
    ap.add_argument('--file',type=Path,required=True)
    args=ap.parse_args()
    if not args.host or not 0<args.port<65536:ap.error('Supply the console host and valid loader port')
    elfcheck.validate(str(args.file));payload=args.file.read_bytes()
    print('ELF sha256',hashlib.sha256(payload).hexdigest(),flush=True)
    with socket.create_connection((args.host,args.port),timeout=10) as sock:
        sock.settimeout(30);sock.sendall(payload)
        print('Transferred',len(payload),'bytes; execution needs a response or console evidence',flush=True)
        sock.settimeout(3);deadline=time.monotonic()+35;total=0
        while time.monotonic()<deadline:
            try:data=sock.recv(65536)
            except socket.timeout:break
            if not data:break
            total+=len(data)
            if total>1048576:raise RuntimeError('Helper output exceeded capture bound')
            print(data.decode('utf8',errors='replace'),end='',flush=True)
if __name__=='__main__':main()
