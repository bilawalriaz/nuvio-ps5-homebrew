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
