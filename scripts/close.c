/* Close Nuvio only, GPL-3.0-or-later.
 * Process enumeration follows SDK v0.43 samples/ps and promote.c.
 * App-info layout follows the recorded firmware 13.60 observation. */
#include <sys/types.h>
#include <sys/proc.h>
#include <sys/user.h>
#include <sys/sysctl.h>
#include <ps5/kernel.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>

typedef struct { uint32_t app_id, flags; uint64_t unknown1;
    char title_id[10]; char unknown2[70]; } app_info_t;
_Static_assert(sizeof(app_info_t)==96,"recorded app-info buffer");
int sceKernelGetAppInfo(pid_t, app_info_t *);

int main(void) {
    if ((kernel_get_fw_version() & UINT32_C(0xffff0000)) != UINT32_C(0x13600000)) {
        puts("NUVIO close refused: unsupported firmware"); return 1;
    }
    int mib[4]={CTL_KERN,KERN_PROC,KERN_PROC_PROC,0};
    size_t size=0;
    if (sysctl(mib,4,NULL,&size,NULL,0) || !size || size>16777216) return 1;
    unsigned char *buf=malloc(size);
    if (!buf) return 1;
    size_t capacity=size;
    if (sysctl(mib,4,buf,&size,NULL,0) || size>capacity) { free(buf); return 1; }
    pid_t target=0; unsigned matches=0;
    for (size_t off=0; off<size;) {
        struct kinfo_proc ki;
        if (size-off<sizeof(ki)) { free(buf); return 1; }
        memcpy(&ki,buf+off,sizeof(ki));
        if (ki.ki_structsize<=0 || (size_t)ki.ki_structsize<sizeof(ki) ||
            (size_t)ki.ki_structsize>size-off) { free(buf); return 1; }
        if (!memcmp(ki.ki_comm,"eboot.bin",sizeof("eboot.bin"))) {
            app_info_t info={0};
            if (!sceKernelGetAppInfo(ki.ki_pid,&info) &&
                !memcmp(info.title_id,"PPSA99997",10)) {
                target=ki.ki_pid; matches++;
            }
        }
        off+=(size_t)ki.ki_structsize;
    }
    free(buf);
    if (!matches) { puts("NUVIO close: no matching process"); return 0; }
    if (matches!=1 || target<=0) { puts("NUVIO close refused: ambiguous process"); return 1; }
    app_info_t confirm={0};
    if (sceKernelGetAppInfo(target,&confirm) || memcmp(confirm.title_id,"PPSA99997",10)) {
        puts("NUVIO close refused: identity changed"); return 1;
    }
#ifdef NUVIO_READ_CREDENTIALS
    uint8_t caps[16];
    uint64_t auth=kernel_get_ucred_authid(target);
    if (!auth || kernel_get_ucred_caps(target,caps)) {
        puts("NUVIO credentials: read failed"); return 1;
    }
    printf("NUVIO credentials authid=%016llx caps=",(unsigned long long)auth);
    for (size_t i=0;i<sizeof(caps);i++) printf("%02x",caps[i]);
    puts(""); return 0;
#else
    if (kill(target,SIGTERM)) { perror("NUVIO close SIGTERM"); return 1; }
    for (int i=0; i<50; i++) {
        if (kill(target,0)<0) {
            if (errno==ESRCH) { puts("NUVIO close: process exited"); return 0; }
            perror("NUVIO close status"); return 1;
        }
        usleep(100000);
    }
    puts("NUVIO close: termination sent, process still present"); return 1;
#endif
}
