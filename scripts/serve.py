#!/usr/bin/env python3
"""Serve only the built Nuvio UI and an optional generated playback fixture."""
import argparse
import http.server
import json
import mimetypes
from pathlib import Path
import re
import subprocess
import urllib.parse

from build import WORK


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.respond(False)

    def do_HEAD(self):
        self.respond(True)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Range')
        self.send_header('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS')
        self.end_headers()

    def respond(self, head):
        path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
        route = path.removeprefix('/ps5-test/')
        if path.startswith('/ps5-test/') and route.endswith('.json'):
            meta = {'id': 'ps5-generated-test', 'type': 'movie',
                    'name': 'PS5 playback test', 'description': 'Generated 720p AVC + AAC test pattern. No library credentials required.'}
            resources = {
                'manifest.json': {'id': 'local.ps5.nuvio.test', 'version': '1.0.0',
                                  'name': 'PS5 Playback Test', 'description': meta['description'],
                                  'resources': ['catalog','meta','stream'], 'types': ['movie'],
                                  'catalogs': [{'type':'movie','id':'ps5-test','name':'PS5 Playback Test'}],
                                  'idPrefixes': ['ps5-generated-']},
                'catalog/movie/ps5-test.json': {'metas': [meta]},
                'meta/movie/ps5-generated-test.json': {'meta': meta},
                'stream/movie/ps5-generated-test.json': {'streams': [{'name':'PS5 test', 'title':'720p H.264 / AAC', 'url':self.server.origin+'/ps5-test/clip.mp4'}]}
            }
            if route in resources and self.server.clip.exists():
                data = json.dumps(resources[route]).encode()
                self.send_response(200)
                self.headers_for('application/json', len(data))
                self.end_headers()
                if not head:
                    self.wfile.write(data)
                return
            self.send_error(404)
            return
        if path == '/ps5-test/clip.mp4':
            file = self.server.clip
        else:
            file = (self.server.root / (path.lstrip('/') or 'index.html')).resolve()
            if not file.is_relative_to(self.server.root):
                self.send_error(403)
                return
        if not file.is_file():
            self.send_error(404)
            return
        size = file.stat().st_size
        start, end = 0, size - 1
        ranged = self.headers.get('Range')
        if ranged:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', ranged)
            if len(ranged) > 128 or not match or not any(match.groups()) or size == 0:
                self.range_error(size)
                return
            left, right = match.groups()
            if left:
                start = int(left)
                end = min(int(right), end) if right else end
            else:
                suffix = int(right)
                if not suffix:
                    self.range_error(size)
                    return
                start = max(0, size-suffix)
            if start >= size or end < start:
                self.range_error(size)
                return
        self.send_response(206 if ranged else 200)
        self.headers_for(mimetypes.guess_type(file.name)[0] or 'application/octet-stream', end-start+1)
        self.send_header('Accept-Ranges', 'bytes')
        if ranged:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        if not head:
            with file.open('rb') as f:
                f.seek(start)
                remaining = end-start+1
                while remaining:
                    data = f.read(min(65536, remaining))
                    if not data:
                        break
                    self.wfile.write(data)
                    remaining -= len(data)

    def headers_for(self, mime, size):
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(size))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')

    def range_error(self, size):
        self.send_response(416)
        self.send_header('Content-Range', f'bytes */{size}')
        self.send_header('Content-Length', '0')
        self.end_headers()


def server(root, clip, host, port, origin):
    httpd = http.server.ThreadingHTTPServer((host, port), Handler)
    httpd.root, httpd.clip, httpd.origin = Path(root).resolve(), Path(clip), origin
    return httpd


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=4173)  # Nuvio's source-defined serve port.
    ap.add_argument('--origin', required=True, help='HTTP origin reachable from PS5; no path or credentials.')
    ap.add_argument('--test-clip', action='store_true')
    args = ap.parse_args()
    parsed = urllib.parse.urlsplit(args.origin)
    if parsed.scheme != 'http' or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        ap.error('--origin must be a plain HTTP origin')
    clip = WORK/'clip.mp4'
    if args.test_clip and not clip.exists():
        run = ['ffmpeg', '-nostdin', '-y', '-f', 'lavfi', '-i', 'testsrc2=size=1280x720:rate=30',
               '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000', '-t', '15',
               '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
               '-c:a', 'aac', '-ac', '2', '-movflags', '+faststart', str(clip)]
        subprocess.run(run, check=True, stdout=subprocess.DEVNULL)
    if not (WORK/'ui/index.html').is_file():
        ap.error('Build the UI with make ui first')
    with server(WORK/'ui', clip, args.host, args.port, args.origin.rstrip('/')) as httpd:
        print('Nuvio UI:', args.origin, '\nTest addon:', args.origin.rstrip('/')+'/ps5-test/manifest.json', flush=True)
        httpd.serve_forever()


if __name__ == '__main__':
    main()
