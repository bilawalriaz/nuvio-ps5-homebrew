"""Execute the adapted upstream network policy without the SDK or network."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build


class NetworkReaderTests(unittest.TestCase):
    def source(self):
        return (ROOT / 'tests/fixtures/network_stream_io.c.txt').read_text()

    def test_network_options_preserve_headers_and_bound_retries(self):
        compiler = shutil.which('clang') or shutil.which('cc')
        if not compiler:
            self.skipTest('No host C compiler')
        text = build.fix_network_reader(self.source())
        self.assertNotIn('ctx->pio = evo_pio_open(', text)
        start = text.index('static int sio_contains_ci(')
        end = text.index('/*\n * Why an open failed', start)
        policy = text[start:end]
        harness = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
typedef struct { char keys[32][64], values[32][256]; int count; } AVDictionary;
static int av_dict_set(AVDictionary **out, const char *key, const char *value, int flags) {
    (void)flags;
    AVDictionary *d=*out;
    assert(d->count < 32 && strlen(key)<64 && strlen(value)<256);
    strcpy(d->keys[d->count],key); strcpy(d->values[d->count++],value);
    return 0;
}
static const char *get(AVDictionary *d,const char *key) {
    for(int i=0;i<d->count;i++) if(!strcmp(d->keys[i],key)) return d->values[i];
    return "";
}
''' + policy + r'''
int main(void) {
    AVDictionary raw={0},playlist={0}; AVDictionary *r=&raw,*p=&playlist;
    strcpy(evo_stream_headers,"Authorization: Bearer fixture\r\n");
    strcpy(evo_stream_user_agent,"fixture-player");
    evo_stream_io_apply_network_options(&r,"https://fixture.invalid/large.mkv");
    assert(!strcmp(get(r,"headers"),evo_stream_headers));
    assert(!strcmp(get(r,"user_agent"),evo_stream_user_agent));
    assert(!strcmp(get(r,"reconnect_on_http_error"),"429,503"));
    assert(!strcmp(get(r,"respect_retry_after"),"1"));
    assert(!strcmp(get(r,"reconnect_max_retries"),"3"));
    assert(!strcmp(get(r,"reconnect_delay_total_max"),"6"));
    assert(!strcmp(get(r,"rw_timeout"),"5000000"));
    assert(!strcmp(get(r,"reconnect_at_eof"),"1"));
    evo_stream_io_apply_network_options(&p,"https://fixture.invalid/master.M3U8?token=x");
    assert(!strcmp(get(p,"reconnect_at_eof"),""));
    assert(!strcmp(get(p,"headers"),evo_stream_headers));
    assert(!strcmp(get(p,"allowed_extensions"),"ALL"));
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'policy.c'
            source.write_text(harness)
            binary = Path(tmp)/'policy'
            subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(source), '-o', str(binary)], check=True, timeout=20)
            subprocess.run([str(binary)], check=True, timeout=5)

    def test_pin_changes_refuse_the_adapter(self):
        for old in ('ctx->pio = evo_pio_open(', 'AVFMT_FLAG_CUSTOM_IO',
                    'av_dict_set(opts, "reconnect_delay_max", "2", 0);'):
            with self.subTest(anchor=old), self.assertRaises(RuntimeError):
                build.fix_network_reader(self.source().replace(old, 'upstream_changed'))
