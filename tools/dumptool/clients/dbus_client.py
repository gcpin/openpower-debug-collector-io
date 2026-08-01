import datetime
import shlex
import subprocess
from typing import List

from dumptool.models import (
    DUMP_CREATE_SPECS,
    DumpEntry,
    DumpInfo,
    DumpType,
    validate_create_parameters,
)


class DBusError(RuntimeError):
    """An actionable failure while communicating with D-Bus through busctl."""


class DBusClient:
    BUSNAME = "xyz.openbmc_project.Dump.Manager"
    DEFAULT_TIMEOUT = 30

    def __init__(self, timeout=DEFAULT_TIMEOUT):
        self.timeout = timeout

    def _run_busctl(self, command, action):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except FileNotFoundError as error:
            raise DBusError(
                "busctl was not found; install systemd busctl before using dumptool"
            ) from error
        except subprocess.TimeoutExpired as error:
            raise DBusError(
                f"{action} timed out after {self.timeout} seconds"
            ) from error

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            if not detail:
                detail = f"busctl exited with status {result.returncode}"
            raise DBusError(f"{action} failed: {detail}")

        return result.stdout.strip()

    # List Dumps
    def list_dumps(self) -> List[DumpEntry]:
        output = self._run_busctl(
            ["busctl", "tree", self.BUSNAME],
            "List dumps",
        )

        dumps = []

        for line in output.splitlines():
            line = line.strip()

            if "/xyz/openbmc_project/dump/" in line and "/entry/" in line:
                path = line.split()[-1]

                dump_id = path.split("/")[-1]

                dumps.append(
                    DumpEntry(
                        id=dump_id,
                        type=DumpType.from_path(path),
                        object_path=path,
                    )
                )

        return dumps

    # Create Dump
    def create_dump(
        self,
        dump_type: DumpType,
        error_log_id=None,
        failing_unit_id=None,
    ) -> str:
        validate_create_parameters(dump_type, error_log_id, failing_unit_id)
        spec = DUMP_CREATE_SPECS[dump_type]

        parameters = []
        if spec.dbus_type is not None:
            parameters.append(
                (
                    "com.ibm.Dump.Create.CreateParameters.DumpType",
                    "s",
                    f"com.ibm.Dump.Create.DumpType.{spec.dbus_type}",
                )
            )
        if error_log_id is not None:
            parameters.append(
                (
                    "com.ibm.Dump.Create.CreateParameters.ErrorLogId",
                    "t",
                    str(error_log_id),
                )
            )
        if failing_unit_id is not None:
            parameters.append(
                (
                    "com.ibm.Dump.Create.CreateParameters.FailingUnitId",
                    "t",
                    str(failing_unit_id),
                )
            )

        cmd = [
            "busctl",
            "call",
            self.BUSNAME,
            dump_type.object_path,
            "xyz.openbmc_project.Dump.Create",
            "CreateDump",
            "a{sv}",
            str(len(parameters)),
        ]
        for key, signature, value in parameters:
            cmd.extend((key, signature, value))

        output = shlex.split(self._run_busctl(cmd, "Create dump"))
        if len(output) != 2 or output[0] != "o" or not output[1].startswith("/"):
            raise DBusError("Create dump failed: invalid object path in response")

        return output[1]

    # Delete Dump
    def delete_dump(self, object_path: str) -> bool:
        self._run_busctl(
            [
                "busctl",
                "call",
                self.BUSNAME,
                object_path,
                "xyz.openbmc_project.Object.Delete",
                "Delete",
            ],
            f"Delete dump {object_path.rsplit('/', 1)[-1]}",
        )

        return True

    # Get Dump Info
    def get_dump_info(self, object_path: str) -> DumpInfo:

        def get_property(prop, interface):
            output_raw = self._run_busctl(
                [
                    "busctl",
                    "get-property",
                    self.BUSNAME,
                    object_path,
                    interface,
                    prop,
                ],
                f"Read {prop} for dump {object_path.rsplit('/', 1)[-1]}",
            )

            output = output_raw.split()

            if len(output) < 2:
                return None

            dtype, value = output[0], output[1]

            if dtype == "b":
                return value.lower() == "true"

            elif dtype in ["u", "t", "x"]:
                return int(value)

            else:
                return value

        def format_time(value):
            if not value or value == 0:
                return None

            try:
                ts = int(value) / 1_000_000
                dt = datetime.datetime.utcfromtimestamp(ts)
                return dt.strftime("%Y-%m-%d %H:%M:%S")

            except Exception:
                return str(value)

        def parse_status(status_raw):
            if not status_raw:
                return None

            if "Completed" in status_raw:
                return True

            elif "InProgress" in status_raw:
                return False

            return None

        def get_subtype():
            output = self._run_busctl(
                [
                    "busctl",
                    "introspect",
                    self.BUSNAME,
                    object_path,
                ],
                f"Inspect dump {object_path.rsplit('/', 1)[-1]}",
            )

            if "com.ibm.Dump.Entry.Hardware" in output:
                return "hardware"

            if "com.ibm.Dump.Entry.Hostboot" in output:
                return "hostboot"

            if "com.ibm.Dump.Entry.SBE" in output:
                return "sbe"

            return DumpType.from_path(object_path).value

        size = get_property(
            "Size",
            "xyz.openbmc_project.Dump.Entry",
        )

        offloaded = get_property(
            "Offloaded",
            "xyz.openbmc_project.Dump.Entry",
        )

        started_time_raw = get_property(
            "StartTime",
            "xyz.openbmc_project.Common.Progress",
        )

        ended_time_raw = get_property(
            "CompletedTime",
            "xyz.openbmc_project.Common.Progress",
        )

        status_raw = get_property(
            "Status",
            "xyz.openbmc_project.Common.Progress",
        )

        completed = parse_status(status_raw)
        started_time = format_time(started_time_raw)
        ended_time = format_time(ended_time_raw)

        dump_id = object_path.split("/")[-1]
        dump_type = DumpType.from_path(object_path)
        subtype = get_subtype()

        return DumpInfo(
            id=dump_id,
            type=dump_type,
            subtype=subtype,
            size=size,
            completed=completed,
            offloaded=offloaded,
            started_time=started_time,
            ended_time=ended_time,
        )
