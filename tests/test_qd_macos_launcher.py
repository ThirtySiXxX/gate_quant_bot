"""Run the macOS launcher only in disposable fixtures with fake interpreters."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


LAUNCHER = Path(__file__).resolve().parents[1] / "启动.command"

VENV_PYTHON = """#!/bin/bash
printf 'VENV:%s\\n' "$*" >> "$QD_FIXTURE_TRACE"
case "$1" in
  -c) exit "${QD_FIXTURE_RUNTIME_STATUS:-0}" ;;
  --version) echo 'Python 3.13.7' ;;
  -m)
    if [ "$*" = '-m pip install -r requirements.txt' ]; then
      exit "${QD_FIXTURE_PIP_STATUS:-0}"
    fi
    [ "$*" = '-m pip install --upgrade pip' ] || exit 91
    ;;
  main.py) printf 'MAIN-CWD:%s\\n' "$PWD" >> "$QD_FIXTURE_TRACE" ;;
  *) exit 92 ;;
esac
"""

GLOBAL_PYTHON = """#!/bin/bash
printf 'GLOBAL:%s\\n' "$*" >> "$QD_FIXTURE_TRACE"
case "$1" in
  -c) echo 312 ;;
  --version) echo 'Python 3.12.0' ;;
  -m)
    [ "$*" = '-m venv venv' ] || exit 93
    /bin/mkdir -p venv/bin
    /bin/cp "$QD_FIXTURE_TEMPLATE" venv/bin/python
    /bin/chmod +x venv/bin/python
    ;;
  *) exit 94 ;;
esac
"""


class MacOSLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gate launcher fixture ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "moved project with spaces"
        self.project.mkdir()
        shutil.copyfile(LAUNCHER, self.project / LAUNCHER.name)
        (self.project / "main.py").write_text("raise AssertionError('real Python must not run main')\n")
        (self.project / "requirements.txt").write_text("fixture-only-not-a-real-dependency\n")
        self.bin = self.root / "commands"
        self.bin.mkdir()
        for name in ("dirname", "touch"):
            (self.bin / name).symlink_to(shutil.which(name))
        self.trace = self.root / "trace"
        self.template = self.root / "fake-venv-python"
        self.template.write_text(VENV_PYTHON)
        self.env = dict(os.environ, PATH=str(self.bin),
                        QD_FIXTURE_TRACE=str(self.trace), QD_FIXTURE_TEMPLATE=str(self.template))
        self.env.pop("QD_FIXTURE_RUNTIME_STATUS", None)
        self.env.pop("QD_FIXTURE_PIP_STATUS", None)

    def existing_environment(self, ready=True, interpreter=True):
        directory = self.project / "venv" / "bin"
        directory.mkdir(parents=True)
        if interpreter:
            shutil.copyfile(self.template, directory / "python")
            (directory / "python").chmod(0o755)
        # Simulates an activation file embedded with the pre-move project path.
        (directory / "activate").write_text(
            'printf "ACTIVATION-SOURCED\\n" >> "$QD_FIXTURE_TRACE"\n'
            'VIRTUAL_ENV="/old/QT/gate_quant_bot/venv"\n'
            'PATH="$VIRTUAL_ENV/bin:/nonexistent"\nexport PATH VIRTUAL_ENV\n')
        if ready:
            (self.project / "venv" / ".deps_ok").touch()

    def global_candidates(self):
        for name in ("python3.12", "python3.11", "python3", "python"):
            executable = self.bin / name
            executable.write_text(GLOBAL_PYTHON)
            executable.chmod(0o755)

    def run_launcher(self):
        result = subprocess.run(["/bin/bash", str(self.project / LAUNCHER.name)],
                                cwd=self.root, env=self.env, input="\n" * 10,
                                text=True, capture_output=True, timeout=10)
        calls = self.trace.read_text().splitlines() if self.trace.exists() else []
        self.assertNotIn("ACTIVATION-SOURCED", calls)
        return result, calls

    def assert_main_started(self, result, calls):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(calls.count("VENV:main.py"), 1)
        self.assertIn("MAIN-CWD:" + str(self.project), calls)

    def test_ready_moved_environment_works_without_global_python(self):
        self.existing_environment()
        result, calls = self.run_launcher()
        self.assert_main_started(result, calls)
        self.assertTrue(any(call.startswith("VENV:-c ") for call in calls))
        self.assertFalse(any("pip" in call or call.startswith("GLOBAL:") for call in calls))

    def test_existing_environment_installs_missing_dependencies_with_own_python(self):
        self.existing_environment(ready=False)
        result, calls = self.run_launcher()
        self.assert_main_started(result, calls)
        self.assertIn("VENV:-m pip install --upgrade pip", calls)
        self.assertIn("VENV:-m pip install -r requirements.txt", calls)
        self.assertTrue((self.project / "venv" / ".deps_ok").is_file())
        self.assertFalse(any(call.startswith("GLOBAL:") for call in calls))

    def test_ready_environment_is_preferred_to_available_global_candidates(self):
        self.existing_environment()
        self.global_candidates()
        result, calls = self.run_launcher()
        self.assert_main_started(result, calls)
        self.assertFalse(any(call.startswith("GLOBAL:") for call in calls))

    def test_broken_environment_fails_with_or_without_dependency_marker(self):
        self.global_candidates()
        self.existing_environment()
        interpreter = self.project / "venv" / "bin" / "python"
        before = interpreter.read_bytes()
        for ready in (True, False):
            for status in (1, 126):
                with self.subTest(ready=ready, runtime_exit=status):
                    marker = self.project / "venv" / ".deps_ok"
                    if not ready and marker.exists():
                        marker.unlink()
                    self.trace.unlink(missing_ok=True)
                    self.env["QD_FIXTURE_RUNTIME_STATUS"] = str(status)
                    result, calls = self.run_launcher()
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn("venv/bin/python", result.stdout)
                    self.assertFalse(any(call.startswith("GLOBAL:") or "pip" in call or "main.py" in call for call in calls))
                    self.assertEqual(interpreter.read_bytes(), before)
                    self.assertEqual(marker.exists(), ready)

    def test_missing_environment_interpreter_does_not_trigger_recreation_or_fallback(self):
        self.global_candidates()
        self.existing_environment(interpreter=False)
        result, calls = self.run_launcher()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("venv/bin/python", result.stdout)
        self.assertEqual(calls, [])
        self.assertFalse((self.project / "venv" / "bin" / "python").exists())
        self.assertTrue((self.project / "venv" / ".deps_ok").exists())

    def test_first_run_creates_environment_then_uses_its_interpreter(self):
        self.global_candidates()
        result, calls = self.run_launcher()
        self.assert_main_started(result, calls)
        self.assertEqual([call for call in calls if call.startswith("GLOBAL:")],
                         ["GLOBAL:-c import sys; print(\"%d%d\" % sys.version_info[:2])",
                          "GLOBAL:-m venv venv"])
        self.assertIn("VENV:-m pip install -r requirements.txt", calls)
        self.assertTrue((self.project / "venv" / ".deps_ok").exists())

    def test_dependency_install_failure_does_not_mark_ready_or_start_main(self):
        self.existing_environment(ready=False)
        self.env["QD_FIXTURE_PIP_STATUS"] = "1"
        result, calls = self.run_launcher()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("依赖安装失败", result.stdout)
        self.assertIn("VENV:-m pip install -r requirements.txt", calls)
        self.assertNotIn("VENV:main.py", calls)
        self.assertFalse((self.project / "venv" / ".deps_ok").exists())


if __name__ == "__main__":
    unittest.main()
