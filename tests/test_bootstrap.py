"""Actual C bootstrap transport over host sockets, with a labelled fake helper."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
HARNESS=r'''
#include "bootstrap.h"
#include <sys/socket.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
int main(int argc,char **argv) {
    if(argc!=2) return 2;
    int pair[2]; if(socketpair(AF_UNIX,SOCK_STREAM,0,pair)) return 3;
    size_t length=131071;
    unsigned char *payload=malloc(length); if(!payload) return 4;
    for(size_t i=0;i<length;i++) payload[i]=(unsigned char)i;
    pid_t child=fork(); if(child<0) return 5;
    if(!child) {
        close(pair[0]);
        if(!strcmp(argv[1],"drop")) { close(pair[1]); _exit(0); }
        unsigned char block[127]; size_t got=0;
        while(got<length) {
            size_t count=length-got<sizeof(block)?length-got:sizeof(block);
            ssize_t n=read(pair[1],block,count); if(n<=0) _exit(6);
            for(ssize_t j=0;j<n;j++) if(block[j]!=(unsigned char)(got+(size_t)j)) _exit(7);
            got+=(size_t)n;
        }
        const char *ack="NUVIO promote verified: native network privileges applied\n";
        if(!strcmp(argv[1],"wrong")) ack="Transferred ELF; no process evidence\n";
        if(!strcmp(argv[1],"partial")) ack="NUVIO promote verified: native network privileges applied";
        if(!strcmp(argv[1],"already")) ack="NUVIO promote verified: privileges already applied\n";
        if(!strcmp(argv[1],"overflow")) {
            for(int i=0;i<5000;i++) if(send(pair[1],"x",1,MSG_NOSIGNAL)<=0) break;
        } else {
            for(size_t i=0;i<strlen(ack);i++) if(send(pair[1],ack+i,1,MSG_NOSIGNAL)<=0) _exit(8);
        }
        close(pair[1]); _exit(0);
    }
    close(pair[1]);
    int flags=fcntl(pair[0],F_GETFL,0);
    if(flags<0 || fcntl(pair[0],F_SETFL,flags|O_NONBLOCK)<0) return 9;
    int result=nuvio_bootstrap_transfer(pair[0],payload,length);
    close(pair[0]); free(payload); int status=0; waitpid(child,&status,0);
    printf("result=%d child=%d\n",result,WIFEXITED(status)?WEXITSTATUS(status):-1);
    return 0;
}
'''

class BootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler=shutil.which('clang') or shutil.which('cc')
        if not compiler: raise unittest.SkipTest('Host C compiler unavailable')
        cls.tmp=tempfile.TemporaryDirectory();cls.directory=Path(cls.tmp.name)
        (cls.directory/'nuvio_bootstrap_blob.h').write_text(
            '#define NUVIO_BOOTSTRAP_PORT 9021\nstatic const unsigned char nuvio_bootstrap_elf[]={0};\n')
        (cls.directory/'harness.c').write_text(HARNESS);cls.exe=cls.directory/'test'
        flags=['-fsanitize=address,undefined','-fno-omit-frame-pointer'] if os.environ.get('NUVIO_HOST_SANITIZERS')=='1' else []
        subprocess.run([compiler,'-std=c11','-O1','-Wall','-Wextra','-Werror',*flags,
            '-I',str(ROOT/'scripts'),'-I',str(cls.directory),str(ROOT/'scripts/bootstrap.c'),
            str(cls.directory/'harness.c'),'-o',str(cls.exe)],check=True,capture_output=True)
    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()
    def run_mode(self,mode):
        return subprocess.check_output([str(self.exe),mode],text=True,timeout=15).strip()
    def test_exact_large_transfer_and_fragmented_process_response(self):
        self.assertEqual(self.run_mode('ok'),'result=0 child=0')
        self.assertEqual(self.run_mode('already'),'result=0 child=0')
    def test_transfer_and_partial_response_are_not_process_evidence(self):
        self.assertEqual(self.run_mode('wrong'),'result=-1 child=0')
        self.assertEqual(self.run_mode('partial'),'result=-1 child=0')
    def test_response_capture_is_bounded(self):
        self.assertEqual(self.run_mode('overflow'),'result=-1 child=0')
    def test_disconnected_loader_cannot_terminate_the_title(self):
        self.assertEqual(self.run_mode('drop'),'result=-1 child=0')
