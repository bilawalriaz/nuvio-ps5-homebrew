/* Run the adapted EVO stream reader without the player UI or decoder.
 * URLs come from a private file and are never printed. */
#include "evo_stream_io.h"
#include "evo_parallel_io.h"
#include <libavutil/time.h>
#include <libavutil/log.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

void *evo_direct_mem_calloc(size_t count, size_t size) { return calloc(count, size); }
void evo_direct_mem_free(void *ptr) { free(ptr); }
void evo_error_set(const char *fmt, ...) { (void)fmt; }
void evo_error_url_host(const char *url, char *out, size_t cap)
{ (void)url; if (cap) out[0] = 0; }
int evo_playlist_sniff_is_channel_list(const char *buf, size_t n)
{ (void)buf; (void)n; return 0; }
void pp_stage_bc(const char *stage, const char *detail)
{
    /* The other stages include a private URL. */
    if (!strcmp(stage, "P8_01d1_HTTP_READER"))
        printf("reader: %s\n", detail);
}
void evo_boot_log(const char *fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    vprintf(fmt, args);
    va_end(args);
    putchar('\n');
}

#ifndef NUVIO_PROBE_CONSOLE
/* Host-only substitutes for the console cache allocation, with matching
 * signatures. The actual network reader and worker code are unchanged. */
static void *cache_mem;
int32_t sceKernelAllocateDirectMemory(int64_t start, int64_t end, size_t len,
                                      size_t align, int type, int64_t *offset)
{
    (void)start; (void)end; (void)align; (void)type;
    cache_mem = calloc(1, len);
    *offset = 0;
    return cache_mem ? 0 : -1;
}
int32_t sceKernelMapDirectMemory(void **addr, size_t len, int prot, int flags,
                                 int64_t offset, size_t align)
{
    (void)len; (void)prot; (void)flags; (void)offset; (void)align;
    *addr = cache_mem;
    return cache_mem ? 0 : -1;
}
int32_t sceKernelReleaseDirectMemory(int64_t start, size_t len)
{ (void)start; (void)len; free(cache_mem); cache_mem = NULL; return 0; }
int32_t sceKernelMunmap(void *addr, size_t len)
{ (void)addr; (void)len; return 0; }
#endif

static int probe(const char *path)
{
    char url[2048];
    FILE *file = fopen(path, "r");
    if (!file) { puts("probe: missing URL file"); return 1; }
    if (!fgets(url, sizeof url, file) || !strchr(url, '\n')) {
        fclose(file); puts("probe: invalid URL file"); return 1;
    }
    fclose(file);
    url[strcspn(url, "\r\n")] = 0;
    av_log_set_level(AV_LOG_QUIET);
    AVFormatContext *fmt = NULL;
    evo_stream_io_ctx_t *io = NULL;
    int64_t start = av_gettime_relative();
    int rc = evo_stream_io_open(url, &fmt, NULL, &io);
    printf("probe: open rc=%d ms=%lld\n", rc,
           (long long)((av_gettime_relative() - start) / 1000));
    if (rc < 0) return 1;
    printf("probe: custom_io=%d\n", !!(fmt->flags & AVFMT_FLAG_CUSTOM_IO));
    evo_stream_io_set_deadline(io, 12);
    rc = avformat_find_stream_info(fmt, NULL);
    evo_stream_io_set_deadline(io, 0);
    printf("probe: stream_info rc=%d streams=%u\n", rc, fmt->nb_streams);
    int video = rc < 0 ? -1 : av_find_best_stream(fmt, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
    AVPacket *pkt = av_packet_alloc();
    int failed = video < 0 || !pkt;
    const double targets[] = { 12, 60, 100, 30, 371.664, 411.664, 422.731, 835.083, 120 };
    int tested = 0;
    for (size_t i = 0; !failed && i < sizeof targets / sizeof targets[0]; i++) {
        double target = targets[i];
        if (fmt->duration > 0 && target >= fmt->duration / (double)AV_TIME_BASE - 2)
            continue;
        start = av_gettime_relative();
        evo_stream_io_set_deadline(io, 12);
        rc = av_seek_frame(fmt, video, (int64_t)(target / av_q2d(fmt->streams[video]->time_base)),
                           AVSEEK_FLAG_BACKWARD);
        double at = -1;
        for (int n = 0; rc >= 0 && n < 3000 && at < target; n++) {
            rc = av_read_frame(fmt, pkt);
            if (rc >= 0 && pkt->stream_index == video && pkt->pts != AV_NOPTS_VALUE)
                at = pkt->pts * av_q2d(fmt->streams[video]->time_base);
            av_packet_unref(pkt);
        }
        evo_stream_io_set_deadline(io, 0);
        int ok = rc >= 0 && at >= target && at < target + 5;
        printf("probe: seek target=%.3f pts=%.3f rc=%d ms=%lld %s\n", target, at, rc,
               (long long)((av_gettime_relative() - start) / 1000), ok ? "PASS" : "FAIL");
        tested++;
        failed = !ok;
    }
    av_packet_free(&pkt);
    avformat_close_input(&fmt);
    evo_stream_io_close(io);
    printf("probe: done seeks=%d result=%s\n", tested, failed || !tested ? "FAIL" : "PASS");
    return failed || !tested;
}

int main(int argc, char **argv)
{
    setvbuf(stdout, NULL, _IONBF, 0);
#ifdef NUVIO_PROBE_CONSOLE
    (void)argc; (void)argv;
    return probe("/data/homebrew/ps5-homebrew-dev/nuvio-seek-url.txt");
#else
    if (argc != 2) { puts("usage: network_seek_probe URL_FILE"); return 1; }
    const char *headers = getenv("NUVIO_PROBE_HEADERS");
    if (headers && strlen(headers) < sizeof evo_stream_headers)
        strcpy(evo_stream_headers, headers);
    return probe(argv[1]);
#endif
}
