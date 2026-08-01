import contextlib
import io
import json
import unittest
from unittest.mock import patch

from dumptool import cli
from dumptool.models import DumpInfo, DumpType
from dumptool.services.dump_service import DumpService, DumpWaitTimeout


def make_info(dump_id, start_time, status="Completed"):
    return DumpInfo(
        id=dump_id,
        type=DumpType.SYSTEM,
        subtype="hardware",
        object_path=f"/xyz/openbmc_project/dump/system/entry/{dump_id}",
        size=1024,
        started_time_us=start_time,
        operation_status=f"example.OperationStatus.{status}",
    )


class StructuredOutputTests(unittest.TestCase):
    @patch.object(cli.service, "list_dumps")
    def test_list_json_is_machine_readable(self, list_dumps):
        list_dumps.return_value = [make_info("00000001", 10)]
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            cli.list_dumps(output_format="json")

        document = json.loads(output.getvalue())
        self.assertEqual(document[0]["id"], "00000001")
        self.assertEqual(document[0]["status"], "Completed")
        self.assertEqual(document[0]["size_bytes"], 1024)

    @patch.object(cli.service, "get_dump_info")
    def test_get_info_json_contains_diagnostic_fields(self, get_info):
        get_info.return_value = make_info("00000001", 10)
        get_info.return_value.error_log_id = 42
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            cli.get_dump_info("00000001", "json")

        document = json.loads(output.getvalue())
        self.assertEqual(document["error_log_id"], 42)
        self.assertEqual(document["type"], "hardware")

    @patch.object(cli.service, "create_dump")
    def test_create_json_reports_requested_entry(self, create):
        create.return_value = (
            "/xyz/openbmc_project/dump/system/entry/00000001"
        )
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            status = cli.create_dump("hardware", 42, 7, "json")

        document = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(document["id"], "00000001")
        self.assertEqual(document["status"], "Requested")


class SelectionTests(unittest.TestCase):
    def test_latest_selects_newest_entries(self):
        entries = [
            make_info("1", 10),
            make_info("2", 30),
            make_info("3", 20),
        ]

        selected = cli._select_dumps(entries, None, None, False, 2)

        self.assertEqual([entry.id for entry in selected], ["2", "3"])

    def test_system_filter_includes_subtypes_before_sorting(self):
        entries = [make_info("2", 30), make_info("1", 10)]

        selected = cli._select_dumps(entries, "system", "id", False, None)

        self.assertEqual([entry.id for entry in selected], ["1", "2"])

    def test_latest_and_sort_are_rejected(self):
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            status = cli.main(["list", "--latest", "2", "--sort", "id"])

        self.assertEqual(status, 2)
        self.assertIn("cannot be combined", stderr.getvalue())

    def test_timeout_requires_wait(self):
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            status = cli.main(
                [
                    "create",
                    "--type",
                    "hostboot",
                    "--error-id",
                    "1",
                    "--timeout",
                    "5",
                ]
            )

        self.assertEqual(status, 2)
        self.assertIn("--timeout requires --wait", stderr.getvalue())


class WaitTests(unittest.TestCase):
    @patch.object(cli.service, "wait_for_dump")
    @patch.object(cli.service, "create_dump")
    def test_create_wait_returns_completed_json(self, create, wait):
        create.return_value = (
            "/xyz/openbmc_project/dump/system/entry/00000001"
        )
        wait.return_value = make_info("00000001", 10)
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            status = cli.create_dump(
                "hardware",
                42,
                7,
                output_format="json",
                wait=True,
                timeout=5,
            )

        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "Completed")
        wait.assert_called_once_with(
            "00000001",
            5,
            object_path=(
                "/xyz/openbmc_project/dump/system/entry/00000001"
            ),
        )

    @patch.object(cli.service, "wait_for_dump")
    @patch.object(cli.service, "create_dump")
    def test_create_wait_returns_failure_for_failed_dump(self, create, wait):
        create.return_value = (
            "/xyz/openbmc_project/dump/system/entry/00000001"
        )
        wait.return_value = make_info("00000001", 10, "Failed")
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = cli.create_dump(
                "hardware",
                42,
                7,
                output_format="json",
                wait=True,
                timeout=5,
            )

        self.assertEqual(status, 1)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "Failed")
        self.assertIn("ended with status Failed", stderr.getvalue())

    def test_service_waits_until_terminal_state(self):
        service = DumpService()
        in_progress = make_info("1", 10, "InProgress")
        completed = make_info("1", 10, "Completed")

        with patch.object(
            service.client,
            "get_dump_info",
            side_effect=(in_progress, completed),
        ), patch("dumptool.services.dump_service.time.sleep"):
            result = service.wait_for_dump(
                "1",
                timeout=5,
                object_path="/xyz/openbmc_project/dump/bmc/entry/1",
            )

        self.assertIs(result, completed)

    def test_service_wait_timeout_is_actionable(self):
        service = DumpService()
        in_progress = make_info("1", 10, "InProgress")

        with patch.object(
            service.client,
            "get_dump_info",
            return_value=in_progress,
        ), patch(
            "dumptool.services.dump_service.time.monotonic",
            side_effect=(0, 2),
        ):
            with self.assertRaisesRegex(
                DumpWaitTimeout,
                "did not complete within 1 second",
            ):
                service.wait_for_dump(
                    "1",
                    timeout=1,
                    object_path="/xyz/openbmc_project/dump/bmc/entry/1",
                )


if __name__ == "__main__":
    unittest.main()
