/* Submit the embedded Nuvio-only helper to the existing loopback ELF loader.
 * GPL-3.0-or-later. No external payload path, address or process input. */
#include "bootstrap.h"
#include "nuvio_bootstrap_blob.h"
#include <sys/socket.h>
#include <netinet/in.h>
#include <poll.h>

#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <time.h>
#include <unistd.h>

static int64_t now_ms(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC,&t)) return -1;
    return (int64_t)t.tv_sec*1000+t.tv_nsec/1000000;
}
static int ready(int fd, short event, int64_t deadline) {
    for (;;) {
        int64_t now=now_ms();
        if (now<0) return -1;
        if (now>=deadline) { errno=ETIMEDOUT; return -1; }
        struct pollfd p={fd,event,0};
        int rc=poll(&p,1,(int)(deadline-now));
        if (rc>0) return 0;
        if (!rc) { errno=ETIMEDOUT; return -1; }
        if (errno!=EINTR) return -1;
    }
}
int nuvio_bootstrap_transfer(int fd, const unsigned char *payload, size_t length) {
    if (!payload || !length || length>1048576) { errno=EINVAL; return -1; }
    int64_t now=now_ms();
    if (now<0) return -1;
    int64_t deadline=now+12000;
    size_t sent=0;
    while (sent<length) {
        if (ready(fd,POLLOUT,deadline)) return -1;
        ssize_t n=send(fd,payload+sent,length-sent,MSG_NOSIGNAL);
        if (n>0) sent+=(size_t)n;
        else if (n<0 && (errno==EINTR || errno==EAGAIN || errno==EWOULDBLOCK)) continue;
        else { if (!n) errno=EPIPE; return -1; }
    }
    char response[4096]; size_t used=0; response[0]='\0';
    while (used<sizeof(response)-1) {
        if (ready(fd,POLLIN,deadline)) return -1;
        ssize_t n=recv(fd,response+used,sizeof(response)-1-used,0);
        if (n>0) {
            used+=(size_t)n; response[used]='\0';
            if (strstr(response,"NUVIO promote verified: native network privileges applied\n") ||
                strstr(response,"NUVIO promote verified: privileges already applied\n")) return 0;
        } else if (n<0 && (errno==EINTR || errno==EAGAIN || errno==EWOULDBLOCK)) continue;
        else { if (!n) errno=EPROTO; return -1; }
    }
    errno=EOVERFLOW; return -1;
}
static const char *stage="idle";
const char *nuvio_bootstrap_stage(void) { return stage; }
int nuvio_bootstrap(void) {
    stage="socket";
#ifndef SOCK_NONBLOCK
    errno=ENOTSUP; return -1;
#else
    int fd=socket(AF_INET,SOCK_STREAM|SOCK_NONBLOCK,0);
    if (fd<0) return -1;
    int result=-1;
    struct sockaddr_in address={0};
#ifdef __FreeBSD__
    address.sin_len=sizeof(address);
#endif
    address.sin_family=AF_INET;
    address.sin_port=htons(NUVIO_BOOTSTRAP_PORT);
    address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    stage="connect";
    if (connect(fd,(struct sockaddr *)&address,sizeof(address))<0) {
        if (errno!=EINPROGRESS) goto done;
        stage="connect-wait";
        int64_t now=now_ms();
        if (now<0 || ready(fd,POLLOUT,now+5000)) goto done;
        stage="connect-status";
        int error=0; socklen_t size=sizeof(error);
        if (getsockopt(fd,SOL_SOCKET,SO_ERROR,&error,&size)) goto done;
        if (error) { errno=error; goto done; }
    }
    stage="transfer";
    result=nuvio_bootstrap_transfer(fd,nuvio_bootstrap_elf,sizeof(nuvio_bootstrap_elf));
done:;
    int saved=errno;
    close(fd); errno=saved; return result;
#endif
}
