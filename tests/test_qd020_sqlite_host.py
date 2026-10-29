"""Host bootstrap tests do not open an account or alter financial sources."""
import json
import importlib.util
import os
import io
import tarfile
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from research.qd019 import sqlite_host as h


class SQLiteHostChecks(unittest.TestCase):
    def test_overlay_keeps_all_other_source_pins(self):
        base={'old.py':'a','kept.py':'b'}
        release=dict(manifest_sha256='m',sqlite_host_fix=dict(schema='qd020.sqlite-host-fix.v1',base_manifest_sha256='m',
                     replacements={'old.py':dict(before='a',after='new')},additional={'host.py':'c'}))
        self.assertEqual(h.admitted_code_pins(base,release),{'old.py':'new','kept.py':'b','host.py':'c'})
        self.assertEqual(base,{'old.py':'a','kept.py':'b'})
        release['sqlite_host_fix']['replacements']['old.py']['before']='wrong'
        with self.assertRaisesRegex(ValueError,'BASE_CODE'):h.admitted_code_pins(base,release)

    def test_builtin_host_never_falls_back_to_system_sqlite(self):
        import types
        db=types.SimpleNamespace(sqlite_version='3.50.4');native=types.SimpleNamespace()
        def imp(name):return db if name=='sqlite3' else native
        with patch.object(h.importlib,'import_module',side_effect=imp),patch.object(h.sys,'platform','linux'),patch.object(h.platform,'machine',return_value='x86_64'),patch.object(h.importlib.metadata,'version',side_effect=h.importlib.metadata.PackageNotFoundError):
            with self.assertRaisesRegex(ValueError,'INSTALL_REQUIREMENTS'):h.select_backend()

    def test_real_shared_connection_write_and_quota_rejection(self):
        result=subprocess.run([sys.executable,'-B','-c',
            'import json;from research.qd019.sqlite_host import prepare_sqlite_host;print(json.dumps(prepare_sqlite_host()))'],
            text=True,capture_output=True,check=True)
        r=json.loads(result.stdout);self.assertTrue(r['vfs_probe']['writes_observed'])
        self.assertTrue(r['vfs_probe']['oversized_write_rejected']);self.assertFalse(r['vfs_probe']['account_files_opened'])

    def test_backend_hash_is_required_before_binding(self):
        import types
        db=types.SimpleNamespace(sqlite_version='3.50.4');native=types.SimpleNamespace();candidate=types.SimpleNamespace();ext=types.SimpleNamespace(__file__='candidate.so')
        modules={'sqlite3':db,'_sqlite3':native,'pysqlite3':candidate,'pysqlite3._sqlite3':ext}
        with patch.object(h.importlib,'import_module',side_effect=lambda n:modules[n]),patch.object(h.sys,'platform','linux'),patch.object(h.platform,'machine',return_value='x86_64'),patch.object(h.importlib.metadata,'version',return_value=h.VERSION),patch.object(h,'sha',return_value='wrong'),patch.object(h,'bind_backend',side_effect=AssertionError('must not bind')):
            with self.assertRaisesRegex(ValueError,'BINARY_HASH'):h.select_backend()

    def test_failed_start_receipt_preserves_and_debits_original_evidence(self):
        path=Path(__file__).resolve().parents[1]/'scripts/qd020/apply-fix.py'
        spec=importlib.util.spec_from_file_location('qd020_installer_test',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'local-logs').mkdir()
            text=b"AttributeError:module '_sqlite3' has no attribute '__file__'\n"
            log=root/'local-logs/qd019-20261029T074000Z.log';log.write_bytes(text)
            archive=root/'return-to-codex-20261029T074002190598Z.tar.gz'
            with tarfile.open(archive,'w:gz') as t:
                info=tarfile.TarInfo('run/console.log');info.size=len(text);t.addfile(info,io.BytesIO(text))
            patch_data=dict(base_manifest_sha256='m',reported_failure=dict(filename=archive.name,sha256=module.sha(archive)))
            before=log.read_bytes(),archive.read_bytes()
            with patch.object(module.os,'cpu_count',return_value=8):r=module.failure_receipt(root,patch_data)
            self.assertEqual(r['wall_seconds_upper_bound'],4);self.assertEqual(r['cpu_seconds_upper_bound'],32)
            self.assertEqual(r['preadmission_failures'],1);self.assertEqual(before,(log.read_bytes(),archive.read_bytes()))


if __name__=='__main__':unittest.main()
