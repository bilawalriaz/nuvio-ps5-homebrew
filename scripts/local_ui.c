/* Serve packaged Nuvio assets through the native title's existing listener.
 * SPDX-License-Identifier: GPL-3.0-or-later */
#include "local_ui.h"
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

/* Shared with the existing payload server; no additional listener is opened. */
int nuvio_ui_path(const char *, const char *, char *, size_t);
const char *nuvio_ui_mime(const char *);

#define LOCAL_PATH_MAX 2048
#define LOCAL_HTML_MAX (1024u * 1024u)

static int local_send_all(int fd, const char *bytes, size_t count)
{
    while (count) {
        /* Browser teardown can close a connection during an asset transfer. */
        ssize_t sent = send(fd, bytes, count, MSG_NOSIGNAL);
        if (sent < 0 && errno == EINTR) continue;
        if (sent <= 0) return -1;
        bytes += (size_t)sent;
        count -= (size_t)sent;
    }
    return 0;
}

static int local_head(int fd, int status, const char *reason,
                       const char *mime, uint64_t size)
{
    char head[384];
    int n = snprintf(head, sizeof head,
                     "HTTP/1.1 %d %s\r\nContent-Type: %s\r\n"
                     "Content-Length: %llu\r\nCache-Control: no-cache\r\n"
                     "Connection: close\r\n\r\n", status, reason, mime,
                     (unsigned long long)size);
    if (n <= 0 || (size_t)n >= sizeof head) return -1;
    return local_send_all(fd, head, (size_t)n);
}

static int local_error(int fd, int status, const char *reason)
{
    return local_head(fd, status, reason, "text/plain", 0) == 0 ? status : -1;
}

static int local_open(const char *root, char *relative)
{
    /* Native title openat raises SIGSYS on the target boot. Check each
     * component with ordinary open and O_NOFOLLOW instead. Installation
     * updates require the title to be closed, so this tree stays stable. */
    char full[LOCAL_PATH_MAX];
    int n = snprintf(full, sizeof full, "%s%s", root, relative);
    if (n < 0 || (size_t)n >= sizeof full) { errno = ENAMETOOLONG; return -1; }
    size_t root_len = strlen(root);
    int directory = open(root, O_RDONLY | O_DIRECTORY | O_NOFOLLOW);
    if (directory < 0) return -1;
    close(directory);
    for (char *part = full + root_len + 1; ; part++) {
        if (*part && *part != '/') continue;
        char separator = *part;
        *part = '\0';
        int child = open(full, O_RDONLY | O_NOFOLLOW | (separator ? O_DIRECTORY : 0));
        *part = separator;
        if (child < 0 || !separator) return child;
        close(child);
    }
}

int nuvio_local_ui_send(int fd, const char *root, const char *method,
                        const char *target, const char *hook, size_t hook_len)
{
    if (!root || !method || !target || (hook_len && !hook))
        return local_error(fd, 500, "Internal Server Error");
    int head_only = !strcmp(method, "HEAD");
    if (strcmp(method, "GET") && !head_only)
        return local_error(fd, 405, "Method Not Allowed");
    char path[LOCAL_PATH_MAX];
    if (target[0] != '/' || nuvio_ui_path("", target, path, sizeof path) != 0)
        return local_error(fd, 403, "Forbidden");
    const char *mime = nuvio_ui_mime(path);
    int file = local_open(root, path);
    if (file < 0)
        return local_error(fd, errno == ELOOP ? 403 : 404,
                           errno == ELOOP ? "Forbidden" : "Not Found");
    struct stat st;
    if (fstat(file, &st) != 0 || !S_ISREG(st.st_mode) || st.st_size < 0) {
        close(file);
        return local_error(fd, 404, "Not Found");
    }
    uint64_t file_size = (uint64_t)st.st_size;
    char *html = NULL;
    size_t insertion = 0, html_size = 0;
    int result = -1;
    if (hook_len && !strncmp(mime, "text/html", 9)) {
        if (file_size > LOCAL_HTML_MAX || hook_len > LOCAL_HTML_MAX) {
            close(file);
            return local_error(fd, 413, "Payload Too Large");
        }
        html_size = (size_t)file_size;
        html = malloc(html_size + 1);
        if (!html) {
            close(file);
            return local_error(fd, 500, "Internal Server Error");
        }
        size_t have = 0;
        while (have < html_size) {
            ssize_t n = read(file, html + have, html_size - have);
            if (n < 0 && errno == EINTR) continue;
            if (n <= 0) goto cleanup;
            have += (size_t)n;
        }
        html[html_size] = '\0';
        /* Bounded scan, including head attributes. No NUL-based search can
         * mistake a truncated read for a complete document. */
        for (size_t i = 0; i + 5 < html_size; i++) {
            if (strncasecmp(html + i, "<head", 5)) continue;
            char boundary = html[i + 5];
            if (boundary != '>' && boundary != ' ' && boundary != '\t' &&
                boundary != '\r' && boundary != '\n') continue;
            char *end = memchr(html + i + 5, '>', html_size - i - 5);
            if (end) insertion = (size_t)(end - html) + 1;
            break;
        }
        file_size += (uint64_t)hook_len; /* Both terms are bounded by 1 MiB. */
    } else {
        hook_len = 0;
    }
    if (local_head(fd, 200, "OK", mime, file_size) != 0) goto cleanup;
    if (head_only) { result = 200; goto cleanup; }
    if (html) {
        if (local_send_all(fd, html, insertion) != 0 ||
            local_send_all(fd, hook, hook_len) != 0 ||
            local_send_all(fd, html + insertion, html_size - insertion) != 0)
            goto cleanup;
    } else {
        char bytes[16384];
        uint64_t left = file_size;
        while (left) {
            size_t want = left < sizeof bytes ? (size_t)left : sizeof bytes;
            ssize_t n = read(file, bytes, want);
            if (n < 0 && errno == EINTR) continue;
            if (n <= 0 || local_send_all(fd, bytes, (size_t)n) != 0) goto cleanup;
            left -= (uint64_t)n;
        }
    }
    result = 200;
cleanup:
    free(html);
    close(file);
    return result;
}
