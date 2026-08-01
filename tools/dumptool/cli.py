#!/usr/bin/env python3

import argparse
from pathlib import Path
import platform
import shutil
import sys

from dumptool import __version__
from dumptool.clients.dbus_client import DBusError
from dumptool.models import (
    DUMP_CREATE_SPECS,
    DumpType,
    validate_create_parameters,
)
from dumptool.services.dump_service import DumpService

service = DumpService()


def list_dumps(filter_type):
    dumps = service.list_dumps()

    print(
        f"{'ID':<10} {'Type':<18} {'Size':<12} {'Start Time (UTC)':<21} "
        f"{'End Time (UTC)':<21} {'Status':<15}"
    )

    for dump in dumps:
        if filter_type:
            matches_subtype = dump.final_type == filter_type
            matches_system_family = (
                filter_type == DumpType.SYSTEM.value
                and dump.type == DumpType.SYSTEM
            )
            if not matches_subtype and not matches_system_family:
                continue

        print(
            f"{dump.id:<10} "
            f"{dump.final_type:<18} "
            f"{dump.size_kb:<12} "
            f"{str(dump.started_time or '-'): <21} "
            f"{str(dump.ended_time or '-'): <21} "
            f"{dump.status:<15}"
        )


def create_dump(dump_type, error_id, failing_id):
    dump_type = DumpType(dump_type)
    validate_create_parameters(dump_type, error_id, failing_id)

    result = service.create_dump(
        dump_type,
        error_log_id=error_id,
        failing_unit_id=failing_id,
    )

    dump_id = result.rsplit("/", 1)[-1]
    print("✔ Dump created successfully")
    print(f"Dump ID : {dump_id}")


def delete_dump(dump_id):
    service.delete_dump(dump_id)
    print("Dump deleted successfully")


def get_dump_info(dump_id):
    info = service.get_dump_info(dump_id)

    print(f"ID           : {info.id}")
    print(f"Type         : {info.final_type}")
    print(f"Object Path  : {info.object_path or 'N/A'}")
    print(f"Size         : {info.size_kb}")
    print(f"Start Time   : {info.started_time or 'N/A'}")
    print(f"End Time     : {info.ended_time or 'N/A'}")
    print(f"Status       : {info.status}")
    print(f"Raw Status   : {info.operation_status or 'N/A'}")
    print(f"Offloaded    : {info.offloaded}")
    print(f"Offload URI  : {info.offload_uri or 'N/A'}")
    if info.error_log_id is not None:
        print(f"Error Log ID : 0x{info.error_log_id:08X} ({info.error_log_id})")
    if info.failing_unit_id is not None:
        print(f"Failing Unit : {info.failing_unit_id}")
    if info.sbe_dump_trigger_type is not None:
        print(f"SBE Trigger  : {info.sbe_dump_trigger_type}")
    if info.dump_files_path is not None:
        print(f"Files Path   : {info.dump_files_path}")


def doctor():
    """Report installation and D-Bus readiness without modifying the system."""
    print(f"dumptool version : {__version__}")
    print(f"Python version   : {platform.python_version()}")
    print(f"Python module    : {Path(__file__).resolve()}")
    print(
        "Create types     : "
        + ", ".join(dump_type.value for dump_type in DUMP_CREATE_SPECS)
    )

    busctl_path = shutil.which("busctl")
    if not busctl_path:
        print("busctl           : NOT FOUND")
        print("Dump manager     : NOT CHECKED")
        return 1

    print(f"busctl           : {busctl_path}")
    try:
        entries = service.client.list_dumps()
    except DBusError as error:
        print(f"Dump manager     : UNAVAILABLE ({error})")
        return 1

    print(f"Dump manager     : available ({len(entries)} entries discovered)")
    return 0


def _create_requirements():
    lines = []
    for dump_type, spec in DUMP_CREATE_SPECS.items():
        required = []
        if spec.requires_error_log_id:
            required.append("--error-id")
        if spec.requires_failing_unit_id:
            required.append("--failing-id")
        requirement = "no IDs" if not required else " and ".join(required)
        lines.append(f"  {dump_type.value:<10} {requirement}")
    return "\n".join(lines)


def build_parser():
    description = f"""Manage OpenBMC dumps through xyz.openbmc_project.Dump.Manager.

Creation requirements:
{_create_requirements()}

ERROR_ID must be the real PEL/error-log ID associated with the failure.
IDs accept decimal or 0x-prefixed hexadecimal notation."""

    parser = argparse.ArgumentParser(
        prog="dumptool",
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  dumptool list
  dumptool create --type bmc
  dumptool create --type hardware --error-id 0x1234ABCD --failing-id 1
  dumptool get-info 00000001
  dumptool doctor

Run 'dumptool <command> --help' for command-specific guidance.""",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="Commands",
        metavar="<command>",
        required=True,
    )

    list_parser = subparsers.add_parser(
        "list",
        help="List available dumps",
        description=(
            "List dump entries. The system filter includes hostboot, hardware, "
            "SBE, memory-buffer SBE, resource, and generic system entries."
        ),
        epilog="Examples:\n  dumptool list\n  dumptool list --type sbe",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    list_parser.add_argument(
        "--type",
        choices=[dump_type.value for dump_type in DumpType],
        help="Show only this type; 'system' includes all system subtypes.",
    )

    create_parser = subparsers.add_parser(
        "create",
        help="Create a dump",
        description=f"""Create a dump and print its D-Bus entry ID.

Required parameters by type:
{_create_requirements()}

Use the real associated PEL/error-log ID; example values are not substitutes
for diagnostic correlation data.""",
        epilog="""Examples:
  dumptool create --type bmc
  dumptool create --type hostboot --error-id 0x1234ABCD
  dumptool create --type hardware --error-id 0x1234ABCD --failing-id 1
  dumptool create --type sbe --error-id 0x1234ABCD --failing-id 1""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    create_parser.add_argument(
        "--type",
        required=True,
        choices=[dump_type.value for dump_type in DUMP_CREATE_SPECS],
        help="Type of dump to create.",
    )
    create_parser.add_argument(
        "--error-id",
        type=lambda value: int(value, 0),
        metavar="PEL_ID",
        help=(
            "Associated PEL/error-log ID in decimal or 0x-prefixed hexadecimal "
            "notation. Required for hostboot, hardware, and sbe."
        ),
    )
    create_parser.add_argument(
        "--failing-id",
        type=lambda value: int(value, 0),
        metavar="UNIT_ID",
        help=(
            "Failing unit's FAPI position in decimal or 0x-prefixed hexadecimal "
            "notation. Required for hardware and sbe."
        ),
    )

    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete a dump",
        description=(
            "Delete one dump entry and its associated dump data. The operation "
            "cannot be undone."
        ),
    )
    delete_parser.add_argument(
        "dump_id",
        metavar="DUMP_ID",
        help="Dump ID to delete; use the exact ID displayed by 'dumptool list'.",
    )

    info_parser = subparsers.add_parser(
        "get-info",
        help="Show dump information",
        description=(
            "Display status, size, timestamps, object path, offload state, and "
            "available dump-type-specific diagnostic fields."
        ),
    )
    info_parser.add_argument(
        "dump_id",
        metavar="DUMP_ID",
        help="Dump ID; use the exact ID displayed by 'dumptool list'.",
    )

    subparsers.add_parser(
        "doctor",
        help="Check installation and D-Bus readiness",
        description=(
            "Print the loaded module path, versions, supported creation types, "
            "busctl location, and dump-manager reachability. No state is changed."
        ),
    )

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "list":
            list_dumps(args.type)
        elif args.command == "create":
            create_dump(
                args.type,
                args.error_id,
                args.failing_id,
            )
        elif args.command == "delete":
            delete_dump(args.dump_id)
        elif args.command == "get-info":
            get_dump_info(args.dump_id)
        elif args.command == "doctor":
            return doctor()
    except ValueError as error:
        print(f"dumptool: invalid request: {error}", file=sys.stderr)
        return 2
    except DBusError as error:
        print(f"dumptool: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"dumptool: unexpected failure: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
