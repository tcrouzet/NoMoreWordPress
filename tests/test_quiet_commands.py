import contextlib
import io
import subprocess
import sys
import unittest

from tools.tools import run_quiet


class QuietCommandTests(unittest.TestCase):
    def test_success_hides_stdout_and_stderr(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            run_quiet([sys.executable, '-c', "import sys; print('success'); print('progress', file=sys.stderr)"], cwd=None)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(stderr.getvalue(), '')

    def test_failure_remains_visible_and_stops_execution(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(subprocess.CalledProcessError) as error:
                run_quiet([sys.executable, '-c', "import sys; print('context'); print('failure', file=sys.stderr); sys.exit(7)"], cwd=None)
        self.assertEqual(error.exception.returncode, 7)
        self.assertIn('context', stderr.getvalue())
        self.assertIn('failure', stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
