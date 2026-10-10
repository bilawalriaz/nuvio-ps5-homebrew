#!/usr/bin/env python3
"""A/B-test the pinned and adapted EVO readers with host FFmpeg and a rate limit.

Requires host ffmpeg, pkg-config, clang and the extracted pinned EVO source.
The loopback server advertises a 256 MiB file and allows two active responses.
Its MP4 has a short real video followed by padding; no remote media is fetched.
"""
import argparse
import collections
import http.server
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import threading
import time

from build import ROOT, fix_network_reader


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-dir', type=Path, required=True,
                    help='Extracted EVO projects/evoplayer directory')
    ap.add_argument('--out-dir', type=Path, required=True)
    args = ap.parse_args()
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    media = args.source_dir.resolve()/'media'
    # The build tree already carries the adapter. Use the pinned upstream
    # fixture for the A/B source, with the build tree's headers and PIO module.
    original = (ROOT/'tests/fixtures/network_stream_io.c.txt').read_text()
    fixed = fix_network_reader(original)
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi',
                    '-i', 'testsrc2=size=160x90:rate=24', '-t', '128', '-an', '-c:v',
                    'libx264', '-preset', 'ultrafast', '-g', '24', '-b:v', '12M',
                    '-minrate', '12M', '-maxrate', '12M', '-bufsize', '12M',
                    '-x264-params', 'nal-hrd=cbr:filler=1', '-movflags', '+faststart',
                    str(out/'fixture.mp4')], check=True, timeout=60)
    video = (out/'fixture.mp4').read_bytes()
    size = 256 * 1024 * 1024
    lock = threading.Lock()
    stats = collections.Counter()
    events = []

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *args):
            pass

        def do_GET(self):
            with lock:
                stats['requests'] += 1
                busy = stats['active'] >= 2 or self.path == '/blocked.mp4'
                offset = int(re.search(r'bytes=(\d+)-', self.headers.get('Range', 'bytes=0-'))[1])
                events.append({'time': time.monotonic(), 'offset': offset, 'limited': busy})
                if not busy:
                    stats['active'] += 1
                    stats['peak'] = max(stats['peak'], stats['active'])
            if busy:
                with lock:
                    stats['rate_limits'] += 1
                self.send_response(429)
                self.send_header('Retry-After', '1')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            try:
                if self.headers.get('Authorization') != 'Bearer fixture':
                    with lock:
                        stats['bad_headers'] += 1
                    self.send_response(401)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                self.send_response(206)
                self.send_header('Content-Type', 'video/mp4')
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Content-Range', f'bytes {offset}-{size-1}/{size}')
                self.send_header('Content-Length', str(size-offset))
                self.end_headers()
                while offset < size:
                    count = min(65536, size-offset)
                    block = video[offset:offset+count]
                    self.wfile.write(block + bytes(count-len(block)))
                    self.wfile.flush()
                    offset += count
                    with lock:
                        stats['bytes'] += count
                    time.sleep(0.002)
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                pass
            finally:
                with lock:
                    stats['active'] -= 1

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    (out/'url.txt').write_text(f'http://127.0.0.1:{server.server_port}/fixture.mp4\n')
    pkg = shlex.split(subprocess.check_output(
        ['pkg-config', '--cflags', '--libs', 'libavformat', 'libavcodec', 'libavutil'], text=True))
    reports = {}
    try:
        for label, text in (('parallel', original), ('single', fixed), ('blocked', fixed)):
            source = out/(label+'.c')
            source.write_text(text)
            binary = out/label
            command = ['clang', '-std=c11', '-D_DEFAULT_SOURCE', '-DEVO_APP_MODULE',
                       '-O1', '-g', '-fsanitize=address,undefined',
                       '-I'+str(media/'include'), '-I'+str(args.source_dir.resolve()/'include'),
                       str(ROOT/'tests/network_seek_probe.c'), str(source),
                       str(media/'src/evo_parallel_io.c'), *pkg, '-pthread', '-o', str(binary)]
            subprocess.run(command, check=True, timeout=30)
            with lock:
                stats.clear()
                events.clear()
            env = dict(os.environ, NUVIO_PROBE_HEADERS='Authorization: Bearer fixture\r\n')
            (out/'url.txt').write_text(f'http://127.0.0.1:{server.server_port}/' +
                                      ('blocked.mp4\n' if label == 'blocked' else 'fixture.mp4\n'))
            start = time.monotonic()
            try:
                result = subprocess.run([str(binary), str(out/'url.txt')], env=env,
                                        text=True, capture_output=True, timeout=45)
                log = result.stdout + result.stderr
                code = result.returncode
            except subprocess.TimeoutExpired as exc:
                log = (exc.stdout or b'').decode() + (exc.stderr or b'').decode()
                code = 'timeout'
            (out/(label+'.log')).write_text(log)
            # All writers should observe socket close before the next case.
            deadline = time.monotonic()+3
            while stats['active'] and time.monotonic() < deadline:
                time.sleep(0.01)
            with lock:
                reports[label] = {'returncode': code, 'seconds': time.monotonic()-start,
                                  'stats': dict(stats), 'events': list(events)}
            print(label, json.dumps({k:v for k,v in reports[label].items() if k!='events'}), flush=True)
        assert reports['single']['returncode'] == 0, 'Single reader failed the range seeks'
        assert reports['single']['stats'].get('bad_headers', 0) == 0
        assert reports['parallel']['stats'].get('rate_limits', 0) > 0, 'Baseline did not trigger the rate limit'
        assert reports['single']['stats'].get('rate_limits', 0) < reports['parallel']['stats']['rate_limits'], \
            'Single reader did not reduce rate limiting'
        assert reports['blocked']['returncode'] == 1, 'Permanent HTTP429 did not fail the open'
        assert reports['blocked']['seconds'] < 12, 'Permanent HTTP429 exceeded the open budget'
        assert reports['blocked']['stats']['requests'] <= 6, 'Permanent HTTP429 retried too often'
    finally:
        (out/'report.json').write_text(json.dumps(reports, indent=2)+'\n')
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == '__main__':
    main()
