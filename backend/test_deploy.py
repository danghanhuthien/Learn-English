"""Deployment bootstrap tests; never download packages or start a server."""
import subprocess
import unittest
from unittest.mock import patch
import deploy


class DeploymentTests(unittest.TestCase):
    def test_existing_runtime_does_not_install(self):
        with patch.object(deploy, 'runtime_ready', return_value=True), patch.object(deploy.subprocess, 'check_call') as install:
            deploy.ensure_dependencies()
            install.assert_not_called()

    def test_missing_runtime_installs_into_local_vendor(self):
        with patch.object(deploy, 'runtime_ready', side_effect=[False, True]), patch.object(deploy.subprocess, 'check_call') as install:
            deploy.ensure_dependencies()
            command=install.call_args.args[0]
            self.assertEqual(command[0], deploy.sys.executable)
            self.assertIn('--target', command)
            self.assertIn(str(deploy.VENDOR), command)
            self.assertIn(str(deploy.ROOT/'backend'/'requirements.txt'), command)

    def test_install_failure_stops_instead_of_import_crash(self):
        with patch.object(deploy, 'runtime_ready', return_value=False), patch.object(deploy.subprocess, 'check_call', side_effect=subprocess.CalledProcessError(1, ['pip'])):
            with self.assertRaises(SystemExit) as error:
                deploy.ensure_dependencies()
            self.assertIn('installation failed', str(error.exception))

    def test_environment_ports_and_explicit_override(self):
        with patch.dict('os.environ', {'PORT':'40301','SERVER_PORT':'9999'}):
            self.assertEqual(deploy.choose_port(),40301)
            self.assertEqual(deploy.choose_port(40302),40302)
        with patch.dict('os.environ', {'PORT':'','SERVER_PORT':'40301'}):
            self.assertEqual(deploy.choose_port(),40301)
        for invalid in [0,65536,'invalid']:
            with self.assertRaises(SystemExit):
                deploy.choose_port(invalid)


if __name__=='__main__':
    unittest.main()
