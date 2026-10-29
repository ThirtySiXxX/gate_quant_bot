"""Focused rejection checks; actual relocation is tested on a frozen copy."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from research.qd019 import migration as m
from research.qd019.entry import run


class MigrationChecks(unittest.TestCase):
    def test_default_off_does_not_read_data(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('OFF_READ')):
            self.assertEqual(run()['status'], 'OFF')

    def test_inventory_detects_changed_missing_and_added_files(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data';p.mkdir();f=p/'candle.jsonl';f.write_bytes(b'original\n')
            expected=m.inventory(p);self.assertEqual(m.verify_inventory(p,expected),9)
            f.write_bytes(b'changed!\n')
            with self.assertRaisesRegex(ValueError,'INTEGRITY'):m.verify_inventory(p,expected)
            f.unlink()
            with self.assertRaisesRegex(ValueError,'INTEGRITY'):m.verify_inventory(p,expected)
            f.write_bytes(b'original\n');(p/'extra').write_bytes(b'')
            with self.assertRaisesRegex(ValueError,'INTEGRITY'):m.verify_inventory(p,expected)

    def test_io_relocation_is_explicit_and_rejects_escape(self):
        with tempfile.TemporaryDirectory() as d:
            new=Path(d).resolve()
            self.assertEqual(m.relocate_path('/old/qd015/a.db','/old/qd015',new),str(new/'a.db'))
            with self.assertRaisesRegex(ValueError,'UNDECLARED'):m.relocate_path('/other/a','/old/qd015',new)
            with self.assertRaisesRegex(ValueError,'TRAVERSAL'):m.relocate_path('/old/qd015/../outside','/old/qd015',new)
            with self.assertRaisesRegex(ValueError,'UNSAFE'):m.relative(new,'../outside')
            (new/'link').symlink_to(new)
            with self.assertRaisesRegex(ValueError,'SYMLINK'):m.relative(new,'link/x')

    def test_host_build_admission_does_not_ignore_numeric_versions(self):
        expected=dict(python_version='3.13.7',numpy='2.5.2',pandas='3.0.5')
        host=dict(expected,implementation='CPython',python='different Linux GCC build')
        with patch.object(m,'runtime',return_value=host),patch.object(m.sys,'platform','linux'):
            self.assertEqual(m.admit_runtime(expected),host)
        for name in ('python_version','numpy','pandas'):
            with patch.object(m,'runtime',return_value=dict(host,**{name:'wrong'})):
                with self.assertRaises(ValueError):m.admit_runtime(expected)
        with patch.object(m,'runtime',return_value=host),patch.object(m.sys,'platform','win32'):
            with self.assertRaisesRegex(ValueError,'WSL2'):m.admit_runtime(expected)


if __name__=='__main__':unittest.main()
