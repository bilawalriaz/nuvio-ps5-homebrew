/*
 * ui_server.c - serve the Nuvio browser UI from the console itself.
 *
 * The port used to need a computer on the same network: the native title opens
 * the system browser at its loopback proxy (evo_webui.c, 127.0.0.1:8686), and
 * that proxy fetched the UI from a LAN HTTP server. This file removes the
 * computer. [SOURCE-VERIFIED] A PS5 folder title cannot bind the loopback proxy
 * before the Nuvio payload applies the SDK privilege values (errno=13), so the
 * payload is loaded every boot anyway; the UI server runs inside that payload,
 * next to the privilege watcher. One payload grants the title its network access
 * and serves the UI.
 *
 * The server is deliberately single-threaded and driven from the payload's own
 * loop. [TESTED-ON-CONSOLE] A threaded accept loop in the payload died silently
 * after binding, while the same socket served requests when the accept loop ran
 * on the process's main thread. The browser opens several connections at once;
 * they queue in the listen backlog and each is answered in turn.
 *
 * The document root is the installed title folder, so the UI travels with the
 * title and no second install step exists. Only GET and HEAD are answered, every
 * path is decoded and confined below the root, and the server binds the loopback
 * address only. The caller passes the port; nothing is scanned or guessed. */
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>

#define UI_REQ_MAX  (16 * 1024)
#define UI_PATH_MAX 2048
#define UI_LOG_CAP  (96 * 1024)

/* Set by nuvio_ui_server_open, read-only afterwards. */
static char s_root[512];
static int  s_listen_fd = -1;

/* A bounded request log, the only evidence that survives the loader's output
 * socket. One line per request, capped so a stuck browser cannot fill /data. */
static size_t s_log_bytes = 0;

static void ui_note(const char *fmt, ...)
{
    char line[256];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(line, sizeof line, fmt, ap);
    va_end(ap);
    if (n <= 0 || s_log_bytes >= UI_LOG_CAP) return;
    FILE *f = fopen("/data/nuvio/ui.log", "a");
    if (!f) return;
    s_log_bytes += (size_t)fwrite(line, 1, (size_t)n, f);
    fputc('\n', f);
    s_log_bytes++;
    fclose(f);
}

/* Extension lookup, not a fixed table: the Nuvio bundle carries hashed asset
 * names. CSS must report text/css or a strict browser refuses the sheet. */
const char *nuvio_ui_mime(const char *name)
{
    const char *dot = strrchr(name, '.');
    if (!dot) return "application/octet-stream";
    if (!strcasecmp(dot, ".html") || !strcasecmp(dot, ".htm")) return "text/html; charset=utf-8";
    if (!strcasecmp(dot, ".js") || !strcasecmp(dot, ".mjs")) return "text/javascript; charset=utf-8";
    if (!strcasecmp(dot, ".css")) return "text/css; charset=utf-8";
    if (!strcasecmp(dot, ".json") || !strcasecmp(dot, ".map") ||
        !strcasecmp(dot, ".webmanifest")) return "application/json";
    if (!strcasecmp(dot, ".wasm")) return "application/wasm";
    if (!strcasecmp(dot, ".svg")) return "image/svg+xml";
    if (!strcasecmp(dot, ".png")) return "image/png";
    if (!strcasecmp(dot, ".jpg") || !strcasecmp(dot, ".jpeg")) return "image/jpeg";
    if (!strcasecmp(dot, ".gif")) return "image/gif";
    if (!strcasecmp(dot, ".webp")) return "image/webp";
    if (!strcasecmp(dot, ".avif")) return "image/avif";
    if (!strcasecmp(dot, ".ico")) return "image/x-icon";
    if (!strcasecmp(dot, ".bmp")) return "image/bmp";
    if (!strcasecmp(dot, ".woff2")) return "font/woff2";
    if (!strcasecmp(dot, ".woff")) return "font/woff";
    if (!strcasecmp(dot, ".ttf")) return "font/ttf";
    if (!strcasecmp(dot, ".otf")) return "font/otf";
    if (!strcasecmp(dot, ".mp4") || !strcasecmp(dot, ".m4v")) return "video/mp4";
    if (!strcasecmp(dot, ".webm")) return "video/webm";
    if (!strcasecmp(dot, ".m3u8")) return "application/vnd.apple.mpegurl";
    if (!strcasecmp(dot, ".ts")) return "video/mp2t";
    if (!strcasecmp(dot, ".vtt")) return "text/vtt";
    if (!strcasecmp(dot, ".srt")) return "application/x-subrip";
    if (!strcasecmp(dot, ".txt") || !strcasecmp(dot, ".conf")) return "text/plain; charset=utf-8";
    if (!strcasecmp(dot, ".xml")) return "application/xml";
    if (!strcasecmp(dot, ".pdf")) return "application/pdf";
    return "application/octet-stream";
}

static int hexval(int c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

/* Map a request target onto a file below root. 0 on success. The URL is
 * percent-decoded and split on '/'; a ".." segment or a NUL is refused, and the
 * result always starts with root + '/' so it cannot leave the tree. */
int nuvio_ui_path(const char *root, const char *url, char *out, size_t cap)
{
    char clean[UI_PATH_MAX];
    size_t o = 0;
    const char *p = url;
    while (*p && *p != '?' && *p != '#') {
        int c = (unsigned char)*p;
        if (c == '%' && p[1] && p[2]) {
            int hi = hexval((unsigned char)p[1]), lo = hexval((unsigned char)p[2]);
            if (hi >= 0 && lo >= 0) {
                c = hi * 16 + lo;
                p += 3;
            } else {
                p++;
            }
        } else {
            p++;
        }
        if (c == 0 || c == '\\') return -1;
        if (o + 2 >= sizeof clean) return -1;
        clean[o++] = (char)c;
    }
    clean[o] = 0;
    int trailing = o > 0 && clean[o - 1] == '/';
    char rel[UI_PATH_MAX];
    size_t r = 0;
    for (size_t i = 0; i < o;) {
        while (i < o && clean[i] == '/') i++;
        size_t s = i;
        while (i < o && clean[i] != '/') i++;
        size_t n = i - s;
        if (n == 0) continue;
        if (n == 2 && clean[s] == '.' && clean[s + 1] == '.') return -1;
        if (n == 1 && clean[s] == '.') continue;
        if (r + n + 12 >= sizeof rel) return -1;
        if (r) rel[r++] = '/';
        memcpy(rel + r, clean + s, n);
        r += n;
    }
    if (r == 0 || trailing) {
        const char *index = "index.html";
        if (r + 11 >= sizeof rel) return -1;
        if (r) rel[r++] = '/';
        memcpy(rel + r, index, 11);
        r += 10;
    }
    rel[r] = 0;
    int n = snprintf(out, cap, "%s/%s", root, rel);
    return (n > 0 && (size_t)n < cap) ? 0 : -1;
}

static int send_all(int fd, const char *buf, size_t len)
{
    while (len) {
        ssize_t n = send(fd, buf, len, 0);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return -1;
        buf += n;
        len -= (size_t)n;
    }
    return 0;
}

static void reply(int fd, const char *status, const char *body)
{
    char head[256];
    size_t len = body ? strlen(body) : 0;
    int n = snprintf(head, sizeof head,
                     "HTTP/1.1 %s\r\nContent-Type: text/plain; charset=utf-8\r\n"
                     "Content-Length: %zu\r\nCache-Control: no-cache\r\n"
                     "Connection: close\r\n\r\n", status, len);
    if (n > 0) send_all(fd, head, (size_t)n);
    if (body && len) send_all(fd, body, len);
}

static void serve_conn(int fd)
{
    /* The listener is non-blocking so one poll can drain a burst; some systems
     * inherit that flag on the accepted socket, which would make the request
     * read return immediately with nothing. Force the connection blocking. */
    int fl = fcntl(fd, F_GETFL, 0);
    if (fl >= 0 && (fl & O_NONBLOCK)) fcntl(fd, F_SETFL, fl & ~O_NONBLOCK);
    char req[UI_REQ_MAX];
    size_t got = 0;
    struct timeval rt = {1, 0};
    struct timeval wt = {5, 0};
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &rt, sizeof rt);
    setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &wt, sizeof wt);
    for (;;) {
        if (got >= sizeof req - 1) break;
        ssize_t n = recv(fd, req + got, sizeof req - 1 - got, 0);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) break;
        got += (size_t)n;
        req[got] = 0;
        if (strstr(req, "\r\n\r\n")) break;
    }
    if (!got) {
        close(fd);
        return;
    }
    char method[8], target[UI_PATH_MAX];
    if (sscanf(req, "%7s %2047s", method, target) != 2) {
        ui_note("400 bad-request");
        reply(fd, "400 Bad Request", "bad request");
        close(fd);
        return;
    }
    int is_get = !strcmp(method, "GET");
    int is_head = !strcmp(method, "HEAD");
    if (!is_get && !is_head) {
        ui_note("405 %s", method);
        reply(fd, "405 Method Not Allowed", "method not allowed");
        close(fd);
        return;
    }
    char file[UI_PATH_MAX + 600];
    if (nuvio_ui_path(s_root, target, file, sizeof file) != 0) {
        ui_note("403 %s", target);
        reply(fd, "403 Forbidden", "forbidden");
        close(fd);
        return;
    }
    int h = open(file, O_RDONLY);
    struct stat st;
    if (h < 0 || fstat(h, &st) != 0 || !S_ISREG(st.st_mode)) {
        ui_note("404 %s", target);
        if (h >= 0) close(h);
        reply(fd, "404 Not Found", "not found");
        close(fd);
        return;
    }
    char head[400];
    int n = snprintf(head, sizeof head,
                     "HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: %lld\r\n"
                     "Cache-Control: no-cache\r\nConnection: close\r\n\r\n",
                     nuvio_ui_mime(file), (long long)st.st_size);
    ui_note("200 %s", target);
    if (n <= 0 || send_all(fd, head, (size_t)n) != 0) {
        close(h);
        close(fd);
        return;
    }
    if (is_get) {
        char buf[64 * 1024];
        for (;;) {
            ssize_t r = read(h, buf, sizeof buf);
            if (r < 0 && errno == EINTR) continue;
            if (r <= 0) break;
            if (send_all(fd, buf, (size_t)r) != 0) break;
        }
    }
    close(h);
    close(fd);
}

/* Bind 127.0.0.1:<port> and serve root. 0 on success. */
int nuvio_ui_server_open(const char *root, int port)
{
    snprintf(s_root, sizeof s_root, "%s", root);
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return -1;
    int one = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    struct sockaddr_in a;
    memset(&a, 0, sizeof a);
    a.sin_family = AF_INET;
    a.sin_port = htons((uint16_t)port);
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (bind(fd, (struct sockaddr *)&a, sizeof a) != 0 ||
        listen(fd, 16) != 0) {
        close(fd);
        return -1;
    }
    /* Non-blocking accept: one poll drains every queued connection, so a burst
     * of asset requests is not serialised one per poll interval. */
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags >= 0) fcntl(fd, F_SETFL, flags | O_NONBLOCK);
    s_listen_fd = fd;
    return 0;
}

/* Answer every queued connection, waiting at most timeout_ms for the first.
 * Returns 1 if at least one connection was served, 0 otherwise. */
int nuvio_ui_server_poll(int timeout_ms)
{
    if (s_listen_fd < 0) return 0;
    fd_set r;
    FD_ZERO(&r);
    FD_SET(s_listen_fd, &r);
    struct timeval tv;
    tv.tv_sec = timeout_ms / 1000;
    tv.tv_usec = (timeout_ms % 1000) * 1000;
    int s = select(s_listen_fd + 1, &r, NULL, NULL, &tv);
    if (s <= 0) return 0;
    int served = 0;
    while (served < 64) {
        int c = accept(s_listen_fd, NULL, NULL);
        if (c < 0) break;
        serve_conn(c);
        served++;
    }
    return served ? 1 : 0;
}
