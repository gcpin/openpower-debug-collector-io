import contextlib
import io
import subprocess
import unittest
from unittest.mock import patch

from dumptool import cli
from dumptool.clients.dbus_client import DBusClient
from dumptool.models import DumpType, validate_create_parameters


class CreateParameterTests(unittest.TestCase):
    def test_required_parameters(self):
        valid_requests = (
            (DumpType.BMC, None, None),
            (DumpType.HOSTBOOT, 1, None),
            (DumpType.HARDWARE, 1, 2),
            (DumpType.SBE, 1, 2),
        )
        for request in valid_requests:
            with self.subTest(dump_type=request[0]):
                validate_create_parameters(*request)

    def test_missing_parameters_are_rejected(self):
        invalid_requests = (
            (DumpType.HOSTBOOT, None, None),
            (DumpType.HARDWARE, 1, None),
            (DumpType.HARDWARE, None, 2),
            (DumpType.SBE, 1, None),
            (DumpType.SBE, None, 2),
        )
        for request in invalid_requests:
            with self.subTest(dump_type=request[0]):
                with self.assertRaises(ValueError):
                    validate_create_parameters(*request)

    def test_irrelevant_parameters_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "does not accept --error-id"):
            validate_create_parameters(DumpType.BMC, 1, None)

        with self.assertRaisesRegex(
            ValueError, "does not accept --failing-id"
        ):
            validate_create_parameters(DumpType.HOSTBOOT, 1, 2)

    def test_ids_must_fit_uint64(self):
        with self.assertRaisesRegex(ValueError, "--error-id must be between"):
            validate_create_parameters(DumpType.HOSTBOOT, -1, None)

        with self.assertRaisesRegex(
            ValueError, "--failing-id must be between"
        ):
            validate_create_parameters(DumpType.SBE, 1, 1 << 64)


class CreateCommandTests(unittest.TestCase):
    @staticmethod
    def _success(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd,
            0,
            'o "/xyz/openbmc_project/dump/system/entry/20000001"\n',
            "",
        )

    @patch("dumptool.clients.dbus_client.subprocess.run")
    def test_hardware_parameters_are_sent_without_defaults(self, run):
        run.side_effect = self._success

        path = DBusClient().create_dump(DumpType.HARDWARE, 42, 7)

        self.assertEqual(
            path, "/xyz/openbmc_project/dump/system/entry/20000001"
        )
        command = run.call_args.args[0]
        self.assertEqual(command[7], "3")
        self.assertIn("42", command)
        self.assertIn("7", command)
        self.assertNotIn(str(0xDEADBEEF), command)

    @patch("dumptool.clients.dbus_client.subprocess.run")
    def test_hostboot_uses_two_parameters(self, run):
        run.side_effect = self._success

        DBusClient().create_dump(DumpType.HOSTBOOT, 42, None)

        command = run.call_args.args[0]
        self.assertEqual(command[7], "2")
        self.assertNotIn(
            "com.ibm.Dump.Create.CreateParameters.FailingUnitId", command
        )

    @patch("dumptool.clients.dbus_client.subprocess.run")
    def test_bmc_uses_empty_parameter_map(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, 'o "/xyz/openbmc_project/dump/bmc/entry/1"\n', ""
        )

        DBusClient().create_dump(DumpType.BMC)

        command = run.call_args.args[0]
        self.assertEqual(command[7], "0")
        self.assertEqual(len(command), 8)

    @patch("dumptool.clients.dbus_client.subprocess.run")
    def test_invalid_create_response_is_rejected(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, "unexpected\n", ""
        )

        with self.assertRaisesRegex(RuntimeError, "invalid object path"):
            DBusClient().create_dump(DumpType.BMC)

    @patch.object(cli.service, "create_dump")
    def test_cli_prints_created_id(self, create):
        create.return_value = "/xyz/openbmc_project/dump/system/entry/20000001"
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            cli.create_dump("hostboot", 42, None)

        self.assertIn("Dump ID : 20000001", output.getvalue())


if __name__ == "__main__":
    unittest.main()
