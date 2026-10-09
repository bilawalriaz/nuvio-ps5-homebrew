"""Refuse incomplete or ambiguous public SDK signing metadata."""
from pathlib import Path
import sys
import unittest
import json
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build import sdk_install_auth_profile
import package_release


class SigningProfileTests(unittest.TestCase):
    def test_profile_preserves_source_bytes_and_authority(self):
        values = [f'{value:02x}' for value in range(136)]
        continuation = ' ' + chr(92) + chr(10) + ' '
        source = ('AUTHID := 0x3800000000000022\nAUTHINFO := ' +
                  continuation.join((' '.join(values[:68]), ' '.join(values[68:]))) + '\n')
        profile = sdk_install_auth_profile(source)
        self.assertEqual(profile['authority'], '0x3800000000000022')
        self.assertEqual(bytes.fromhex(profile['auth_info']), bytes(range(136)))

    def test_profile_rejects_missing_duplicate_short_and_invalid_fields(self):
        good = 'AUTHID := 0x3800000000000022\nAUTHINFO := ' + '00 ' * 136 + '\n'
        for bad in ('', good + good, good.replace('00 ', 'zz ', 1),
                    good.replace('00 ', '', 1),
                    good.replace('0x3800000000000022', '0x10000000000000000')):
            with self.subTest(source=bad[:50]), self.assertRaises(RuntimeError):
                sdk_install_auth_profile(bad)

    def test_release_refuses_a_permission_profile_before_packaging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'VERSION').write_text('0.1.0-test')
            (root / 'build.json').write_text(json.dumps({
                'title_id': 'PPSA99997', 'auth_profile': 'sdk-install-app'}))
            with patch.object(package_release, 'ROOT', root), \
                 patch.object(package_release, 'WORK', root), \
                 patch.object(sys, 'argv', ['package_release']), \
                 self.assertRaisesRegex(RuntimeError, 'Permission-test signing profiles'):
                package_release.main()
            self.assertFalse((root / 'release').exists())
