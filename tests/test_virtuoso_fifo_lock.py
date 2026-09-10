import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from src.clients.virtuoso_client import VirtuosoClient, DEFAULT_LOCK_PATH
from filelock import FileLock, Timeout

class TestVirtuosoFifoLock(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.lock_path = os.path.join(self.temp_dir.name, "test_virtuoso_fifo.lock")
        self.mock_session = MagicMock()
        self.mock_session.connect.return_value = None
        self.mock_session.execute_command.return_value = (0, "Success", "")
        self.mock_session.read_file.return_value = "RESULT: 42"
        self.client = VirtuosoClient(session=self.mock_session, lock_path=self.lock_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_lock_path_and_custom_lock_path(self):
        default_client = VirtuosoClient(session=self.mock_session)
        self.assertEqual(default_client.lock_path, DEFAULT_LOCK_PATH)
        self.assertIsInstance(default_client.fifo_lock, FileLock)
        self.assertEqual(self.client.lock_path, self.lock_path)

    def test_assisted_run_acquires_lock_successfully(self):
        # When lock is free, assisted_run executes and releases cleanly
        res = self.client.assisted_run("plus(20 22)")
        self.assertEqual(res, "RESULT: 42")
        self.assertFalse(self.client.fifo_lock.is_locked)

    def test_assisted_run_blocks_when_lock_held(self):
        # Configure client with very short timeout for test
        self.client.fifo_lock.timeout = 0.2
        
        # Hold the lock externally
        external_lock = FileLock(self.lock_path)
        with external_lock:
            self.assertTrue(external_lock.is_locked)
            # assisted_run should gracefully return diagnostic message when lock cannot be acquired within 0.2s
            res = self.client.assisted_run("plus(1 1)")
            self.assertIn("Error: Could not acquire Virtuoso FIFO lock", res)
            self.assertIn(self.lock_path, res)

        # Once external lock is released, assisted_run succeeds
        res = self.client.assisted_run("plus(1 1)")
        self.assertEqual(res, "RESULT: 42")

if __name__ == "__main__":
    unittest.main()
