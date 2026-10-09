"""Exercise the actual title-local asset responder through host sockets."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build


class LocalUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('clang') or shutil.which('cc')
        if not compiler:
            raise unittest.SkipTest('A host C compiler is required for local UI tests')
        cls.tmp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.tmp.name)
        harness = cls.directory / 'local_ui_harness.c'
        harness.write_text(r'''
#include "local_ui.h"
#include <errno.h>
#include <stdio.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>
#include <string.h>
int main(int argc, char **argv) {
    int pair[2];
    if (argc != 5 || socketpair(AF_UNIX, SOCK_STREAM, 0, pair)) return 2;
    int dropped = !strcmp(argv[2], "DROP");
    if (dropped) close(pair[0]);
    pid_t pid = fork();
    if (pid < 0) return 2;
    if (!pid) {
        if (!dropped) close(pair[0]);
        int rc = nuvio_local_ui_send(pair[1], argv[1], dropped ? "GET" : argv[2], argv[3],
                                     argv[4], strlen(argv[4]));
        close(pair[1]);
        return dropped ? (rc < 0 ? 0 : 1) : (rc < 0 ? 1 : 0);
    }
    close(pair[1]);
    char bytes[8192];
    while (!dropped) {
        ssize_t n = read(pair[0], bytes, sizeof bytes);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) return 2;
        if (!n) break;
        if (fwrite(bytes, 1, (size_t)n, stdout) != (size_t)n) return 2;
    }
    if (!dropped) close(pair[0]);
    int status;
    if (waitpid(pid, &status, 0) != pid) return 2;
    return WIFEXITED(status) ? WEXITSTATUS(status) : 2;
}
''')
        cls.binary = cls.directory / 'local_ui_harness'
        flags = ['-std=c11', '-Wall', '-Wextra', '-Werror']
        if os.environ.get('NUVIO_HOST_SANITIZERS') == '1':
            flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        subprocess.run([compiler, *flags, '-I', str(ROOT / 'scripts'), str(harness),
                        str(ROOT / 'scripts/local_ui.c'), str(ROOT / 'scripts/ui_server.c'),
                        '-o', str(cls.binary)], check=True, timeout=30)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.files = tempfile.TemporaryDirectory(dir=self.directory)
        self.root = Path(self.files.name) / 'webui'
        self.root.mkdir()
        self.html = b'<html><HEAD data-test="1"><title>Nuvio</title></HEAD><body>fixture</body></html>'
        (self.root / 'index.html').write_bytes(self.html)
        (self.root / 'css').mkdir()
        self.css = b'body{background:black}' * 4096
        (self.root / 'css/bundle.css').write_bytes(self.css)
        self.hook = '<script src="/evo/hook.js"></script>'

    def tearDown(self):
        self.files.cleanup()

    def request(self, path, method='GET', hook=None):
        out = subprocess.run([str(self.binary), str(self.root), method, path,
                              self.hook if hook is None else hook],
                             capture_output=True, check=True, timeout=10).stdout
        head, body = out.split(b'\r\n\r\n', 1)
        lines = head.decode().split('\r\n')
        fields = dict(line.split(': ', 1) for line in lines[1:])
        return int(lines[0].split()[1]), fields, body

    def test_entry_injects_the_existing_bridge_before_page_scripts(self):
        status, fields, body = self.request('/?state=ignored')
        expected = self.html.replace(b'<HEAD data-test="1">',
                                     b'<HEAD data-test="1">' + self.hook.encode())
        self.assertEqual(status, 200)
        self.assertEqual(body, expected)
        self.assertEqual(int(fields['Content-Length']), len(expected))
        self.assertTrue(fields['Content-Type'].startswith('text/html'))
        status, head_fields, body = self.request('/index.html', 'HEAD')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'')
        self.assertEqual(head_fields['Content-Length'], fields['Content-Length'])

    def test_large_assets_stream_with_correct_mime_and_length(self):
        status, fields, body = self.request('/css/bundle.css')
        self.assertEqual(status, 200)
        self.assertTrue(fields['Content-Type'].startswith('text/css'))
        self.assertEqual(body, self.css)
        self.assertEqual(int(fields['Content-Length']), len(body))

    def test_paths_and_symlinks_cannot_escape_the_installed_webui(self):
        outside = Path(self.files.name) / 'private.txt'
        outside.write_bytes(b'private fixture')
        (self.root / 'escape.txt').symlink_to(outside)
        (self.root / 'escape-dir').symlink_to(Path(self.files.name), target_is_directory=True)
        for path in ('/../private.txt', '/%2e%2e/private.txt', '/%00private.txt',
                     '/escape.txt', '/escape-dir/private.txt', '/%5cprivate.txt',
                     'http://fixture.invalid/index.html', '/' + 'a' * 2048):
            with self.subTest(path=path):
                status, _, body = self.request(path)
                self.assertIn(status, (403, 404))
                self.assertNotIn(b'private fixture', body)

    def test_missing_files_methods_and_oversized_html_fail_explicitly(self):
        self.assertEqual(self.request('/missing.js')[0], 404)
        self.assertEqual(self.request('/', 'POST')[0], 405)
        with (self.root / 'index.html').open('wb') as f:
            f.truncate(1024 * 1024 + 1)
        self.assertEqual(self.request('/')[0], 413)

    def test_empty_html_and_head_like_tags_keep_lengths_correct(self):
        for source in (b'', b'<header>not a head</header>', b'<head>ok</head>'):
            (self.root / 'index.html').write_bytes(source)
            status, fields, body = self.request('/')
            self.assertEqual(status, 200)
            self.assertEqual(int(fields['Content-Length']), len(body))
            if source.startswith(b'<header>'):
                self.assertTrue(body.startswith(self.hook.encode()))

    def test_closed_browser_socket_does_not_terminate_the_server_process(self):
        result = subprocess.run([str(self.binary), str(self.root), 'DROP',
                                 '/css/bundle.css', self.hook],
                                capture_output=True, check=True, timeout=10)
        self.assertEqual(result.stdout, b'')


class TitleUIAdapterTests(unittest.TestCase):
    def test_source_anchor_changes_stop_the_adapter(self):
        with self.assertRaises(RuntimeError):
            build.title_ui_sources('changed upstream', 'changed provider')
