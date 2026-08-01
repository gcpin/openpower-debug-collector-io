import contextlib
import io
import subprocess
import unittest
from unittest.mock import patch

from dumptool import cli
from dumptool.clients.dbus_client import DBusClient, DBusError


class DBusErrorTests(unittest.TestCase):
    @patch("dumptool.clients.dbus_client.subprocess.run")
    def test_failed_list_is_not_reported_as_empty(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 1, "", "Failed to connect to bus"
        )

        with self.assertRaisesRegex(DBusError, "Failed to connect to bus"):
            DBusClient().list_dumps()

    @patch("dumptool.clients.dbus_client.subprocess.run")
    def test_missing_busctl_has_actionable_error(self, run):
        run.side_effect = FileNotFoundError()

        with self.assertRaisesRegex(DBusError, "busctl was not found"):
            DBusClient().list_dumps()

    @patch("dumptool.clients.dbus_client.subprocess.run")
    def test_timeout_has_actionable_error(self, run):
        run.side_effect = subprocess.TimeoutExpired(["busctl"], 4)

        with self.assertRaisesRegex(DBusError, "timed out after 4 seconds"):
            DBusClient(timeout=4).list_dumps()

    @patch("dumptool.clients.dbus_client.subprocess.run")
    def test_failed_delete_is_not_reported_as_success(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 1, "", "Delete is not allowed"
        )

        with self.assertRaisesRegex(DBusError, "Delete is not allowed"):
            DBusClient().delete_dump(
                "/xyz/openbmc_project/dump/bmc/entry/1"
            )


class CLIExitCodeTests(unittest.TestCase):
    @patch.object(cli.service, "create_dump")
    def test_dbus_failure_returns_one_and_uses_stderr(self, create):
        create.side_effect = DBusError("Create dump failed: service unavailable")
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = cli.main(
                [
                    "create",
                    "--type",
                    "hostboot",
                    "--error-id",
                    "1",
                ]
            )

        self.assertEqual(status, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("service unavailable", stderr.getvalue())

    def test_invalid_request_returns_two_and_uses_stderr(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = cli.main(["create", "--type", "hostboot"])

        self.assertEqual(status, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("requires --error-id", stderr.getvalue())

    @patch.object(cli.service, "delete_dump")
    def test_delete_failure_does_not_print_success(self, delete):
        delete.side_effect = DBusError("Delete dump 1 failed")
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = cli.main(["delete", "1"])

        self.assertEqual(status, 1)
        self.assertNotIn("success", stdout.getvalue().lower())
        self.assertIn("Delete dump 1 failed", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
