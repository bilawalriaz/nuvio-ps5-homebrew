"""Exercise the upstream pin refresh offline, with a fake GitHub transport."""
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

APP = Path(__file__).resolve().parents[1]/'scripts'
spec = importlib.util.spec_from_file_location('nuvio_upstreams', APP/'update_upstreams.py')
upstreams = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstreams)


class FakeNetwork:
    """Map a URL to canned JSON, or to bytes when the caller wants a body."""

    def __init__(self, routes):
        self.routes = routes

    def json(self, url):
        value = self.routes[url]
        if isinstance(value, bytes):
            raise AssertionError('JSON requested for a binary route: '+url)
        return value

    def body(self, url):
        value = self.routes[url]
        if not isinstance(value, bytes):
            raise AssertionError('Body requested for a JSON route: '+url)
        return value


class ResolveTests(unittest.TestCase):
    def test_release_source_current_pin_reports_no_change(self):
        routes = {'https://api.github.com/repos/NuvioMedia/NuvioTVSmart/releases/latest':
                  {'tag_name': '1.2.1'}}
        pin = {'id': 'nuvio-tv-source', 'release': '1.2.1', 'commit': 'a'*40}
        self.assertIsNone(upstreams.resolve(pin, upstreams.UPSTREAMS['nuvio-tv-source'],
                                            FakeNetwork(routes).json))

    def test_release_source_drift_pins_commit_hash_and_directory(self):
        commit = 'b'*40
        body = b'new source tree'
        routes = {
            'https://api.github.com/repos/NuvioMedia/NuvioTVSmart/releases/latest': {'tag_name': '1.2.2'},
            'https://api.github.com/repos/NuvioMedia/NuvioTVSmart/commits/1.2.2': {'sha': commit},
            f'https://codeload.github.com/NuvioMedia/NuvioTVSmart/tar.gz/{commit}': body,
        }
        network = FakeNetwork(routes)
        pin = {'id': 'nuvio-tv-source', 'release': '1.2.1', 'commit': 'a'*40}
        fields = upstreams.resolve(pin, upstreams.UPSTREAMS['nuvio-tv-source'],
                                   lambda url, binary=False: network.body(url) if binary else network.json(url))
        self.assertEqual(fields['commit'], commit)
        self.assertEqual(fields['release'], '1.2.2')
        self.assertEqual(fields['directory'], 'NuvioTVSmart-'+commit)
        self.assertEqual(fields['sha256'], upstreams.digest(body))
        self.assertEqual(fields['size_bytes'], len(body))
        self.assertEqual(fields['cache_file'], 'nuvio-tv-source-1.2.2.tar.gz')
        self.assertEqual(fields['retrieved'], date.today().isoformat())

    def test_branch_source_drift_uses_head_commit(self):
        commit = 'c'*40
        body = b'evo head tree'
        routes = {
            'https://api.github.com/repos/sainsaji/EVO-PLAYER-PS5/commits/main': {'sha': commit},
            f'https://codeload.github.com/sainsaji/EVO-PLAYER-PS5/tar.gz/{commit}': body,
        }
        network = FakeNetwork(routes)
        pin = {'id': 'evo-player-nuvio-source', 'commit': 'd'*40}
        fields = upstreams.resolve(pin, upstreams.UPSTREAMS['evo-player-nuvio-source'],
                                   lambda url, binary=False: network.body(url) if binary else network.json(url))
        self.assertEqual(fields['commit'], commit)
        self.assertNotIn('release', fields)
        self.assertEqual(fields['directory'], 'EVO-PLAYER-PS5-'+commit)

    def test_release_asset_drift_prefers_published_digest(self):
        body = b'wgt bytes'
        routes = {
            'https://api.github.com/repos/NuvioMedia/NuvioTVSmart/releases/latest': {
                'tag_name': '1.2.2',
                'assets': [{'name': 'NuvioTV-Tizen-1.2.2.wgt', 'browser_download_url': 'https://example.invalid/x.wgt',
                            'size': len(body), 'digest': 'sha256:'+upstreams.digest(body)}]},
            'https://example.invalid/x.wgt': body,
        }
        network = FakeNetwork(routes)
        pin = {'id': 'nuvio-official-tv-config', 'version': '1.2.1'}
        fields = upstreams.resolve(pin, upstreams.UPSTREAMS['nuvio-official-tv-config'],
                                   lambda url, binary=False: network.body(url) if binary else network.json(url))
        self.assertEqual(fields['version'], '1.2.2')
        self.assertEqual(fields['sha256'], upstreams.digest(body))
        self.assertEqual(fields['cache_file'], 'NuvioTV-Tizen-1.2.2.wgt')
        self.assertIn('GitHub reports this asset digest', fields['evidence'])

    def test_release_asset_without_digest_records_local_hash(self):
        body = b'wgt bytes'
        routes = {
            'https://api.github.com/repos/NuvioMedia/NuvioTVSmart/releases/latest': {
                'tag_name': '1.2.2',
                'assets': [{'name': 'NuvioTV-Tizen-1.2.2.wgt', 'browser_download_url': 'https://example.invalid/x.wgt',
                            'size': len(body)}]},
            'https://example.invalid/x.wgt': body,
        }
        network = FakeNetwork(routes)
        pin = {'id': 'nuvio-official-tv-config', 'version': '1.2.1'}
        fields = upstreams.resolve(pin, upstreams.UPSTREAMS['nuvio-official-tv-config'],
                                   lambda url, binary=False: network.body(url) if binary else network.json(url))
        self.assertIn('LOCALLY RECORDED', fields['evidence'])

    def test_missing_release_asset_is_an_error(self):
        routes = {'https://api.github.com/repos/NuvioMedia/NuvioTVSmart/releases/latest':
                  {'tag_name': '1.2.2', 'assets': []}}
        network = FakeNetwork(routes)
        pin = {'id': 'nuvio-official-tv-config', 'version': '1.2.1'}
        with self.assertRaises(RuntimeError):
            upstreams.resolve(pin, upstreams.UPSTREAMS['nuvio-official-tv-config'],
                              lambda url, binary=False: network.body(url) if binary else network.json(url))


class ApplyTests(unittest.TestCase):
    def test_apply_rewrites_deps_lock_and_reports_stale_docs(self):
        commit = 'e'*40
        body = b'new source tree'
        routes = {
            'https://api.github.com/repos/NuvioMedia/NuvioTVSmart/releases/latest': {'tag_name': '1.2.2'},
            'https://api.github.com/repos/NuvioMedia/NuvioTVSmart/commits/1.2.2': {'sha': commit},
            f'https://codeload.github.com/NuvioMedia/NuvioTVSmart/tar.gz/{commit}': body,
        }
        network = FakeNetwork(routes)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'deps.lock').write_text(json.dumps({'manifest_version': 1, 'generated': '2026-01-01',
                'artifacts': [{'id': 'nuvio-tv-source', 'release': '1.2.1', 'commit': 'f'*40,
                               'sha256': upstreams.digest(b'old'), 'url': 'https://example.invalid/old'}]}, indent=2)+'\n')
            (root/'docs').mkdir()
            (root/'docs'/'SOURCES.md').write_text('Nuvio ' + 'f'*40 + '\n')
            (root/'docs'/'OTHER.md').write_text('unrelated\n')
            original = upstreams.ROOT
            upstreams.ROOT = root
            upstreams.get_json = network.json
            upstreams.download = network.body
            argv = sys.argv
            sys.argv = ['update_upstreams.py', '--apply']
            try:
                self.assertEqual(upstreams.main(), 0)
                stale = upstreams.stale_references(['f'*40])
            finally:
                upstreams.ROOT = original
                sys.argv = argv
            pin = json.loads((root/'deps.lock').read_text())['artifacts'][0]
            self.assertEqual(pin['commit'], commit)
            self.assertEqual(pin['release'], '1.2.2')
            self.assertEqual(pin['sha256'], upstreams.digest(body))
            self.assertEqual(json.loads((root/'deps.lock').read_text())['generated'], date.today().isoformat())
            self.assertEqual(stale, ['docs/SOURCES.md'])


if __name__ == '__main__':
    unittest.main()
