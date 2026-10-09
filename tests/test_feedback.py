"""Fresh console evidence, privacy filtering and artifact gates for feedback."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import feedback


class FeedbackTests(unittest.TestCase):
    def test_old_success_cannot_satisfy_a_new_launch(self):
        old = (b'BUILD old\nserver: bind ok 127.0.0.1:8686\n'
               b'server: listen ok port=8686\nserver: connection accepted\npage: route home\n')
        self.assertEqual(feedback.fresh_bytes(old, old), b'')
        self.assertEqual(feedback.classify(feedback.startup_events(b''), 'ui'),
                         'waiting_for_fresh_startup')
        with self.assertRaises(RuntimeError):
            feedback.fresh_bytes(old, b'BUILD rotated\n')

    def test_socket_events_do_not_imply_a_loaded_ui(self):
        data = (b'BUILD test_1009\nserver: socket ok fd=7\n'
                b'server: bind ok 127.0.0.1:8686\nserver: listen ok port=8686\n'
                b'server: connection accepted\n')
        events = feedback.startup_events(data)
        self.assertEqual(feedback.classify(events, 'loopback'), 'loopback_ready')
        self.assertEqual(feedback.classify(events, 'ui'), 'waiting_for_fresh_startup')
        self.assertEqual(feedback.classify(events + ['page: route home'], 'ui'),
                         'ui_route_observed')
        self.assertEqual(feedback.classify(events[1:], 'loopback'), 'waiting_for_fresh_startup')

    def test_embedded_bootstrap_requires_fresh_promotion_evidence(self):
        events = ['BUILD auto', 'server: bind ok 127.0.0.1:8686',
                  'server: listen ok port=8686', 'server: connection accepted']
        self.assertEqual(feedback.classify(events, 'loopback', False, True),
                         'waiting_for_fresh_startup')
        self.assertEqual(feedback.classify(events+['bootstrap: promotion verified errno=0'],
                                          'loopback', False, True), 'loopback_ready')
        self.assertEqual(feedback.classify(events+['bootstrap: promotion failed errno=61'],
                                          'loopback', False, True), 'bootstrap_failed')

    def test_title_ui_gate_requires_a_successful_asset_response(self):
        events = ['BUILD local', 'server: bind ok 127.0.0.1:8686',
                  'server: listen ok port=8686', 'server: connection accepted',
                  'page: route home', 'title-ui: packaged assets selected']
        self.assertEqual(feedback.classify(events, 'ui', True),
                         'waiting_for_fresh_startup')
        self.assertEqual(feedback.classify(events + ['title-ui: response status=404'],
                                          'ui', True), 'waiting_for_fresh_startup')
        self.assertEqual(feedback.classify(events + ['title-ui: response status=200'],
                                          'ui', True), 'ui_route_observed')
        self.assertEqual(feedback.startup_events(
            b'title-ui: response status=200 private-url\n'),
            ['title-ui: response status=200'])

    def test_private_stream_and_login_values_are_not_printable_events(self):
        data = (b'web: url https://private.invalid/secret?token=private\n'
                b'web: server: bind failed port=8686 errno=13 private-token\n'
                b'web: page: route home https://private.invalid/token\n'
                b'BUILD test_1009\nserver: connection accepted')
        events = feedback.startup_events(data)
        self.assertEqual(events, ['server: bind failed port=8686 errno=13',
                                 'page: route home', 'BUILD test_1009'])
        self.assertEqual(feedback.classify(events, 'ui'), 'listener_failed')

    def test_log_read_is_bounded(self):
        class FTP:
            def retrbinary(self, command, callback):
                self.command = command
                callback(b'012345')
        ftp = FTP()
        with patch.object(feedback, 'LOG_LIMIT', 5), self.assertRaises(RuntimeError):
            feedback.read_log(ftp)
        self.assertEqual(ftp.command, 'RETR /data/nuvio/evo.log')

    def test_mismatched_installed_artifact_never_launches(self):
        expected = 'a' * 64
        other = 'b' * 64
        info = json.dumps({'title_id': 'PPSA99997', 'installed': True,
                           'mounted': False, 'source_type': 'folder'})
        hashes = (f'NUVIO eboot installed bytes=100 sha256={other}\n'
                  f'NUVIO eboot backup bytes=100 sha256={other}\n'
                  'NUVIO eboot stage=absent\n')
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / 'build.json'
            receipt.write_text(json.dumps({'title_id': 'PPSA99997',
                                           'files': {'eboot.bin': expected}}))
            with patch.object(sys, 'argv', ['feedback', '--host', 'fixture.invalid',
                    '--ftp-port', '2121', '--receipt', str(receipt)]), \
                 patch.object(feedback, 'verify_helpers'), \
                 patch.object(feedback, 'helper', side_effect=[info, hashes]) as helper, \
                 patch.object(feedback.ftplib, 'FTP') as ftp, \
                 contextlib.redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
                feedback.main()
            self.assertEqual([call.args[0] for call in helper.call_args_list], [2, 5])
            ftp.assert_not_called()

    def test_helper_hash_mismatch_stops_before_console_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / 'control-2.elf').write_bytes(b'changed helper')
            with self.assertRaises(RuntimeError):
                feedback.verify_helpers({'helpers': {'control-2.elf': 'a' * 64}}, directory)

    def test_feedback_reports_only_the_new_launch(self):
        expected = 'a' * 64
        info = json.dumps({'title_id': 'PPSA99997', 'installed': True,
                           'mounted': False, 'source_type': 'folder'})
        hashes = (f'NUVIO eboot installed bytes=100 sha256={expected}\n'
                  f'NUVIO eboot backup bytes=100 sha256={expected}\n'
                  'NUVIO eboot stage=absent\n')
        before = b'BUILD old\npage: route old\n'
        after = before + (b'BUILD new\nserver: bind ok 127.0.0.1:8686\n'
                          b'server: listen ok port=8686\nserver: connection accepted\n'
                          b'private https://private.invalid/token\npage: route home\n')
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / 'build.json'
            receipt.write_text(json.dumps({'title_id': 'PPSA99997',
                                           'files': {'eboot.bin': expected}}))
            output = io.StringIO()
            with patch.object(sys, 'argv', ['feedback', '--host', 'fixture.invalid',
                    '--ftp-port', '2121', '--receipt', str(receipt)]), \
                 patch.object(feedback, 'verify_helpers'), \
                 patch.object(feedback, 'helper', side_effect=[info, hashes, 'accepted']) as helper, \
                 patch.object(feedback.ftplib, 'FTP'), \
                 patch.object(feedback, 'read_log', side_effect=[before, after]), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(feedback.main(), 0)
            self.assertEqual([call.args[0] for call in helper.call_args_list], [2, 5, 3])
            self.assertIn('Feedback: ui_route_observed', output.getvalue())
            self.assertNotIn('BUILD old', output.getvalue())
            self.assertNotIn('private.invalid', output.getvalue())
