import contextlib
import io
import subprocess
import unittest
from unittest.mock import patch

from dumptool import cli
from dumptool.clients.dbus_client import DBusClient
from dumptool.models import DumpInfo, DumpType


class DiscoveryTests(unittest.TestCase):
    @patch("dumptool.clients.dbus_client.subprocess.run")
    def test_tree_parsing_is_exact_deduplicated_and_forward_compatible(
        self, run
    ):
        run.return_value = subprocess.CompletedProcess(
            [],
            0,
            "\n".join(
                (
                    "├─ /xyz/openbmc_project/dump/system/entry/20000001",
                    "├─ /xyz/openbmc_project/dump/system"
                    "/entry/20000001/child",
                    "├─ /xyz/openbmc_project/dump/future/entry/vendor-id",
                    "└─ /xyz/openbmc_project/not_dump/entry/1",
                )
            ),
            "",
        )

        entries = DBusClient().list_dumps()

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].id, "20000001")
        self.assertEqual(entries[0].type, DumpType.SYSTEM)
        self.assertEqual(entries[1].id, "vendor-id")
        self.assertEqual(entries[1].type, DumpType.UNKNOWN)


class DumpInfoTests(unittest.TestCase):
    @staticmethod
    def _property_result(command):
        values = {
            "Size": "t 2048",
            "Offloaded": "b false",
            "OffloadUri": 's "file:///tmp/dump"',
            "StartTime": "t 1000000",
            "CompletedTime": "t 2000000",
            "Status": (
                's "xyz.openbmc_project.Common.Progress'
                '.OperationStatus.Failed"'
            ),
            "ErrorLogId": "t 42",
            "FailingUnitId": "t 7",
            "DumpFilesPath": 's "/run/boot-failure"',
            "SBEDumpTriggerType": (
                's "com.ibm.Dump.Create' '.SBEDumpTriggerType.BootFailure"'
            ),
        }
        return values[command[-1]]

    @patch("dumptool.clients.dbus_client.subprocess.run")
    def test_sbe_details_and_failed_status_are_preserved(self, run):
        def respond(command, **kwargs):
            if command[1] == "introspect":
                stdout = "com.ibm.Dump.Entry.SBE interface"
            else:
                stdout = self._property_result(command)
            return subprocess.CompletedProcess(command, 0, stdout, "")

        run.side_effect = respond
        info = DBusClient().get_dump_info(
            "/xyz/openbmc_project/dump/system/entry/30000001"
        )

        self.assertEqual(info.final_type, "sbe")
        self.assertEqual(info.status, "Failed")
        self.assertEqual(info.error_log_id, 42)
        self.assertEqual(info.failing_unit_id, 7)
        self.assertEqual(info.dump_files_path, "/run/boot-failure")
        self.assertEqual(
            info.sbe_dump_trigger_type,
            "com.ibm.Dump.Create.SBEDumpTriggerType.BootFailure",
        )
        self.assertEqual(info.started_time, "1970-01-01 00:00:01Z")

    @patch("dumptool.clients.dbus_client.subprocess.run")
    def test_memory_buffer_sbe_is_classified_by_id_prefix(self, run):
        def respond(command, **kwargs):
            if command[1] == "introspect":
                stdout = "com.ibm.Dump.Entry.SBE interface"
            elif command[-1] in ("DumpFilesPath", "SBEDumpTriggerType"):
                return subprocess.CompletedProcess(
                    command,
                    1,
                    "",
                    "org.freedesktop.DBus.Error.UnknownProperty",
                )
            else:
                stdout = self._property_result(command)
            return subprocess.CompletedProcess(command, 0, stdout, "")

        run.side_effect = respond
        info = DBusClient().get_dump_info(
            "/xyz/openbmc_project/dump/system/entry/40000001"
        )

        self.assertEqual(info.final_type, "memory-buffer-sbe")

    def test_all_operation_statuses_are_reported(self):
        expected = {
            "NotStarted": "Not Started",
            "InProgress": "In Progress",
            "Completed": "Completed",
            "Failed": "Failed",
            "Aborted": "Aborted",
            "VendorState": "VendorState",
        }
        for raw_status, display_status in expected.items():
            with self.subTest(raw_status=raw_status):
                info = DumpInfo(
                    id="1",
                    type=DumpType.BMC,
                    operation_status=f"example.OperationStatus.{raw_status}",
                )
                self.assertEqual(info.status, display_status)


class FilterAndOutputTests(unittest.TestCase):
    @patch.object(cli.service, "list_dumps")
    def test_system_filter_includes_system_subtypes(self, list_dumps):
        list_dumps.return_value = [
            DumpInfo(
                id="20000001",
                type=DumpType.SYSTEM,
                subtype="hostboot",
                size=1024,
                operation_status="Completed",
            )
        ]
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            cli.list_dumps("system")

        self.assertIn("20000001", output.getvalue())
        self.assertIn("hostboot", output.getvalue())

    @patch.object(cli.service, "get_dump_info")
    def test_get_info_prints_diagnostic_fields(self, get_info):
        get_info.return_value = DumpInfo(
            id="30000001",
            type=DumpType.SYSTEM,
            subtype="sbe",
            object_path="/xyz/openbmc_project/dump/system/entry/30000001",
            operation_status="example.OperationStatus.Failed",
            error_log_id=42,
            failing_unit_id=7,
        )
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            cli.get_dump_info("30000001")

        self.assertIn("0x0000002A (42)", output.getvalue())
        self.assertIn("Failing Unit : 7", output.getvalue())
        self.assertIn("Failed", output.getvalue())


if __name__ == "__main__":
    unittest.main()
