"""Closing must prove process response and unmounted title, not only transfer."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import close


class CloseTests(unittest.TestCase):
    def fixture(self, root):
        helpers={}
        for name in ('close.elf', 'control-2.elf'):
            (root/name).write_bytes(name.encode())
            helpers[name]=hashlib.sha256(name.encode()).hexdigest()
        (root/'build.json').write_text(json.dumps({'title_id':'PPSA99997','helpers':helpers}))

    def test_successful_transfer_without_process_evidence_is_not_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            with patch.object(close,'WORK',root), patch.dict(close.os.environ,PS5_HOST='fixture.invalid'), \
                    patch.object(close.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='Transferred ELF')), \
                    patch.object(close,'helper') as helper, self.assertRaises(RuntimeError):
                close.main()
            helper.assert_not_called()

    def test_process_exit_waits_for_unmounted_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            responses=[json.dumps({'title_id':'PPSA99997','mounted':True}),
                       json.dumps({'title_id':'PPSA99997','mounted':False})]
            with patch.object(close,'WORK',root), patch.dict(close.os.environ,PS5_HOST='fixture.invalid'), \
                    patch.object(close.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='NUVIO close: process exited\n')), \
                    patch.object(close,'helper',side_effect=responses) as helper, \
                    patch.object(close.time,'sleep'):
                self.assertEqual(close.main(),0)
            self.assertEqual(helper.call_count,2)

    def test_changed_helper_cannot_run_on_console(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root);(root/'control-2.elf').write_bytes(b'changed')
            with patch.object(close,'WORK',root), patch.dict(close.os.environ,PS5_HOST='fixture.invalid'), \
                    patch.object(close.subprocess,'run') as run, self.assertRaises(RuntimeError):
                close.main()
            run.assert_not_called()
