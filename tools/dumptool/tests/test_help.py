import contextlib
import io
import unittest
from unittest.mock import patch

from dumptool import __version__, cli
from dumptool.models import DumpEntry, DumpType


class HelpTests(unittest.TestCase):
    def test_top_level_help_documents_creation_contract(self):
        help_text = cli.build_parser().format_help()

        self.assertIn("hostboot   --error-id", help_text)
        self.assertIn("hardware   --error-id and --failing-id", help_text)
        self.assertIn("real PEL/error-log ID", help_text)
        self.assertIn("dumptool doctor", help_text)

    def test_create_help_has_parameter_meanings_and_examples(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                cli.main(["create", "--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("FAPI position", output.getvalue())
        self.assertIn("0x-prefixed", output.getvalue())
        self.assertIn("hexadecimal notation", output.getvalue())
        self.assertIn("--type hardware", output.getvalue())

    def test_version_is_available_without_a_command(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                cli.main(["--version"])

        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(output.getvalue().strip(), f"dumptool {__version__}")


class DoctorTests(unittest.TestCase):
    @patch("dumptool.cli.shutil.which", return_value="/usr/bin/busctl")
    @patch.object(cli.service.client, "list_dumps")
    def test_doctor_reports_loaded_path_and_manager(self, list_dumps, which):
        list_dumps.return_value = [
            DumpEntry(
                id="1",
                type=DumpType.BMC,
                object_path="/xyz/openbmc_project/dump/bmc/entry/1",
            )
        ]
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            status = cli.doctor()

        self.assertEqual(status, 0)
        self.assertIn("dumptool version", output.getvalue())
        self.assertIn("cli.py", output.getvalue())
        self.assertIn("available (1 entries discovered)", output.getvalue())

    @patch("dumptool.cli.shutil.which", return_value=None)
    def test_doctor_fails_cleanly_when_busctl_is_missing(self, which):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            status = cli.doctor()

        self.assertEqual(status, 1)
        self.assertIn("busctl           : NOT FOUND", output.getvalue())
        self.assertIn("Dump manager     : NOT CHECKED", output.getvalue())


if __name__ == "__main__":
    unittest.main()
