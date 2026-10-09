/* Aurora-only registration/launch helper. GPL-3.0-or-later.
 * ShadowMountPlus cd0e11ce: docs/api.md; shsrv 6f320637: bundles/hbldr/hbldr.c.
 * Launch ABI adapted from John Törnblom (C) 2025, GPL-3.0-or-later.
 * No arbitrary paths, commands, network destinations or title IDs. */
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#ifndef AURORA_CONTROL_ACTION
#define AURORA_CONTROL_ACTION 1
#endif
#if AURORA_CONTROL_ACTION == 4
#include <fcntl.h>
#include "../../payloads/common/sha256.h"
int main(void) {
    int root=open("/data/homebrew/ps5-homebrew-dev",O_RDONLY|O_DIRECTORY|O_NOFOLLOW);
    if(root<0) { perror("dev root"); return 1; }
    int stage=openat(root,"aurora-stage-PPSA99998",O_RDONLY|O_DIRECTORY|O_NOFOLLOW); close(root);
    if(stage<0) { perror("stage"); return 1; }
    int module=openat(stage,"sce_module",O_RDONLY|O_DIRECTORY|O_NOFOLLOW); close(stage);
    if(module<0) { perror("module directory"); return 1; }
    int fd=openat(module,"libc.prx",O_RDONLY|O_NOFOLLOW); close(module);
    if(fd<0) { perror("runtime"); return 1; }
    sha256_ctx hash; sha256_init(&hash);
    unsigned char bytes[4096],digest[32]; size_t total=0;
    for(;;) {
        ssize_t n=read(fd,bytes,sizeof(bytes));
        if(n<0 && errno==EINTR) continue;
        if(n<0) { perror("read"); close(fd); return 1; }
        if(n==0) break;
        total+=(size_t)n;
        if(total>16777216) { puts("Runtime exceeds verification bound"); close(fd); return 1; }
        sha256_update(&hash,bytes,(size_t)n);
    }
    close(fd); sha256_final(&hash,digest);
    printf("AURORA runtime bytes=%zu sha256=",total);
    for(size_t i=0;i<sizeof(digest);i++) printf("%02x",digest[i]);
    puts(""); return 0;
}
#elif AURORA_CONTROL_ACTION == 5
#include <fcntl.h>
#include <inttypes.h>
#include "../../payloads/common/sha256.h"

static int hash_fd(int fd, uint8_t digest[SHA256_DIGEST_SIZE], uint64_t *total) {
    sha256_ctx hash;
    uint8_t bytes[16384];
    sha256_init(&hash); *total=0;
    for(;;) {
        ssize_t n=read(fd,bytes,sizeof(bytes));
        if(n<0 && errno==EINTR) continue;
        if(n<0) return -1;
        if(n==0) break;
        if(*total>UINT64_MAX-(uint64_t)n) { errno=EOVERFLOW; return -1; }
        *total+=(uint64_t)n;
        sha256_update(&hash,bytes,(size_t)n);
    }
    sha256_final(&hash,digest); return 0;
}

static void report(const char *kind, uint64_t bytes,
                   const uint8_t digest[SHA256_DIGEST_SIZE]) {
    printf("NUVIO eboot %s bytes=%" PRIu64 " sha256=",kind,bytes);
    for(size_t i=0;i<SHA256_DIGEST_SIZE;i++) printf("%02x",digest[i]);
    puts("");
}

int main(void) {
    int installed=open("/data/homebrew/PPSA99997/eboot.bin",O_RDONLY|O_NOFOLLOW);
    if(installed<0) { perror("installed eboot"); return 1; }
    uint8_t installed_hash[SHA256_DIGEST_SIZE], backup_hash[SHA256_DIGEST_SIZE];
    uint64_t installed_size=0, backup_size=0;
    if(hash_fd(installed,installed_hash,&installed_size)!=0 || installed_size==0 ||
       installed_size>134217728u || lseek(installed,0,SEEK_SET)<0) {
        perror("hash installed eboot"); close(installed); return 1;
    }
    report("installed",installed_size,installed_hash);

    char backup_name[96];
    int n=snprintf(backup_name,sizeof(backup_name),"nuvio-eboot-backup-");
    if(n<0 || (size_t)n>=sizeof(backup_name)) { close(installed); return 1; }
    size_t used=(size_t)n;
    for(size_t i=0;i<SHA256_DIGEST_SIZE;i++) {
        n=snprintf(backup_name+used,sizeof(backup_name)-used,"%02x",installed_hash[i]);
        if(n!=2) { close(installed); return 1; }
        used+=2;
    }
    if(used+5>=sizeof(backup_name)) { close(installed); return 1; }
    memcpy(backup_name+used,".bin",5);
    char backup_path[160];
    n=snprintf(backup_path,sizeof(backup_path),"/data/homebrew/ps5-homebrew-dev/%s",backup_name);
    if(n<0 || (size_t)n>=sizeof(backup_path)) { close(installed); return 1; }
    int backup=open(backup_path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
    if(backup>=0) {
        uint8_t bytes[16384];
        for(;;) {
            ssize_t amount=read(installed,bytes,sizeof(bytes));
            if(amount<0 && errno==EINTR) continue;
            if(amount<0) { perror("read eboot backup source"); close(backup); close(installed); return 1; }
            if(amount==0) break;
            size_t sent=0;
            while(sent<(size_t)amount) {
                ssize_t written=write(backup,bytes+sent,(size_t)amount-sent);
                if(written<0 && errno==EINTR) continue;
                if(written<=0) { perror("write eboot backup"); close(backup); close(installed); return 1; }
                sent+=(size_t)written;
            }
        }
        if(fsync(backup)!=0 || close(backup)!=0) { perror("finish eboot backup"); close(installed); return 1; }
    } else if(errno!=EEXIST) {
        perror("create eboot backup"); close(installed); return 1;
    }
    int backup_read=open(backup_path,O_RDONLY|O_NOFOLLOW);
    if(backup_read<0) {
        perror("open eboot backup"); close(installed); return 1;
    }
    int backup_result=hash_fd(backup_read,backup_hash,&backup_size);
    int backup_close=close(backup_read);
    if(backup_result!=0 || backup_close!=0 || backup_size!=installed_size ||
       memcmp(installed_hash,backup_hash,sizeof(installed_hash))!=0) {
        perror("verify eboot backup"); close(installed); return 1;
    }
    report("backup",backup_size,backup_hash);
    printf("NUVIO eboot backup_path=/data/homebrew/ps5-homebrew-dev/%s\n",backup_name);

    int staged=open("/data/homebrew/PPSA99997/eboot.bin.nuvio-update",O_RDONLY|O_NOFOLLOW);
    if(staged<0 && errno==ENOENT) {
        puts("NUVIO eboot stage=absent");
    } else if(staged<0) {
        perror("staged eboot"); close(installed); return 1;
    } else {
        uint8_t stage_hash[SHA256_DIGEST_SIZE]; uint64_t stage_size=0;
        int result=hash_fd(staged,stage_hash,&stage_size);
        int close_result=close(staged);
        if(result!=0 || close_result!=0 || stage_size==0 || stage_size>134217728u) {
            perror("hash staged eboot"); close(installed); return 1;
        }
        report("stage",stage_size,stage_hash);
    }
    close(installed);
    return 0;
}
#elif AURORA_CONTROL_ACTION == 3
/* Layout and zero-initialized fields follow the upstream hbldr example. */
typedef struct { uint32_t structsize,user_id,app_opt; uint64_t crash_report;
    uint32_t check_flag; char **argv; } LaunchContext;
_Static_assert(sizeof(LaunchContext)==40,"launch ABI");
int sceUserServiceInitialize(void *);
int sceUserServiceGetForegroundUser(uint32_t *);
int sceUserServiceTerminate(void);
int sceSystemServiceGetAppIdOfRunningBigApp(void);
int sceSystemServiceLaunchApp(const char *,char **,LaunchContext *);
int main(void) {
    int owned=sceUserServiceInitialize(NULL)==0;
    LaunchContext context={0};
    int running=sceSystemServiceGetAppIdOfRunningBigApp();
    printf("AURORA running_big_app=%d\n",running);
    if(running>0 || sceUserServiceGetForegroundUser(&context.user_id)!=0) {
        puts("AURORA launch refused: close the running title or sign in first");
        if(owned) sceUserServiceTerminate();
        return 1;
    }
    int result=sceSystemServiceLaunchApp("PPSA99998",NULL,&context);
    printf("AURORA launch_result=0x%x\n",(unsigned)result);
    if(owned) sceUserServiceTerminate();
    return result<0;
}
#else
int main(void) {
#if AURORA_CONTROL_ACTION == 1
    const char *route="/api/v1/manual/add";
    const char *body="{\"path\":\"/data/homebrew/PPSA99998\"}";
#else
    const char *route="/api/v1/games/info";
    const char *body="{\"title_id\":\"PPSA99998\"}";
#endif
    int fd=socket(AF_INET,SOCK_STREAM,0);
    struct timeval timeout={5,0};
    struct sockaddr_in address={0};
    address.sin_len=sizeof(address); address.sin_family=AF_INET;
    address.sin_port=htons(10101); /* Source-defined ShadowMount loopback default. */
    if(fd<0) { perror("socket"); return 1; }
    if(inet_pton(AF_INET,"127.0.0.1",&address.sin_addr)!=1 ||
       setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout))!=0 ||
       setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout))!=0 ||
       connect(fd,(struct sockaddr *)&address,sizeof(address))!=0) {
        perror("ShadowMount loopback"); close(fd); return 1;
    }
    char request[512];
    int count=snprintf(request,sizeof(request),"POST %s HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: %zu\r\nConnection: close\r\n\r\n%s",route,strlen(body),body);
    if(count<0 || (size_t)count>=sizeof(request)) { close(fd); return 1; }
    size_t sent=0;
    while(sent<(size_t)count) {
        ssize_t n=send(fd,request+sent,(size_t)count-sent,0);
        if(n<0 && errno==EINTR) continue;
        if(n<=0) { perror("send"); close(fd); return 1; }
        sent+=(size_t)n;
    }
    size_t total=0; char buffer[4096];
    while(total<131072) {
        ssize_t n=recv(fd,buffer,sizeof(buffer),0);
        if(n<0 && errno==EINTR) continue;
        if(n==0) { close(fd); return total==0; }
        if(n<0) { perror("recv"); close(fd); return 1; }
        if(fwrite(buffer,1,(size_t)n,stdout)!=(size_t)n) { close(fd); return 1; }
        total+=(size_t)n;
    }
    puts("AURORA response limit reached"); close(fd); return 1;
}
#endif
