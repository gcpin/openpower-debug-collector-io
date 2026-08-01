#!/usr/bin/env python3

import argparse
import sys

from dumptool.models import (
    DUMP_CREATE_SPECS,
    DumpType,
    validate_create_parameters,
)
from dumptool.clients.dbus_client import DBusError
from dumptool.services.dump_service import DumpService

service = DumpService()


def list_dumps(filter_type):
    dumps = service.list_dumps()

    print(
        f"{'ID':<10} {'Type':<12} {'Size(KB)':<12} {'Start Time':<20} {'End Time':<20} {'Status':<15}"
    )

    for d in dumps:
        if filter_type:
            matches_subtype = d.final_type == filter_type
            matches_system_family = (
                filter_type == DumpType.SYSTEM.value
                and d.type == DumpType.SYSTEM
            )
            if not matches_subtype and not matches_system_family:
                continue

        print(
            f"{d.id:<10} "
            f"{d.final_type:<12} "
            f"{d.size_kb:<12} "
            f"{str(d.started_time or '-'): <20} "
            f"{str(d.ended_time or '-'): <20} "
            f"{d.status:<15}"
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
    print(f"Size (KB)    : {info.size_kb}")
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


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="dumptool",
        description="""
OpenBMC Dump Management Tool

Supported dump types:
  bmc
  hostboot
  hardware
  sbe
""",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  dumptool list
  dumptool list --type bmc
  dumptool list --type hostboot
  dumptool list --type hardware
  dumptool list --type sbe

  dumptool create --type bmc
  dumptool create --type hostboot --error-id <ERROR_ID>
  dumptool create --type hardware --error-id <ERROR_ID> --failing-id <FAILING_UNIT_ID>
  dumptool create --type sbe --error-id <ERROR_ID> --failing-id <FAILING_UNIT_ID>

  dumptool get-info <DUMP_ID>
  dumptool delete <DUMP_ID>

Placeholders:
  <ERROR_ID>         Error Log ID (e.g. 0xDEADBEEF)
  <FAILING_UNIT_ID>  Failing Unit ID (e.g. 1)
  <DUMP_ID>          Dump ID
""",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="Commands",
        metavar="<command>",
        required=True,
    )

    # ---------------- LIST ----------------
    list_parser = subparsers.add_parser(
        "list",
        help="List available dumps",
        description="List all available dumps.",
    )

    list_parser.add_argument(
        "--type",
        choices=[
            "bmc",
            "system",
            "resource",
            "faultlog",
            "hostboot",
            "hardware",
            "sbe",
            "memory-buffer-sbe",
            "unknown",
        ],
        help="Filter dumps by type.",
    )

    # ---------------- CREATE ----------------
    create_parser = subparsers.add_parser(
        "create",
        help="Create a dump",
        description="Create a new dump.",
    )

    create_parser.add_argument(
        "--type",
        required=True,
        choices=[dump_type.value for dump_type in DUMP_CREATE_SPECS],
        help="Type of dump to create.",
    )

    create_parser.add_argument(
        "--error-id",
        type=lambda x: int(x, 0),
        help="Error Log ID (required for hostboot, hardware, and sbe).",
    )

    create_parser.add_argument(
        "--failing-id",
        type=lambda x: int(x, 0),
        help="Failing Unit ID (required for hardware and sbe).",
    )

    # ---------------- DELETE ----------------
    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete a dump",
        description="Delete a dump by ID.",
    )

    delete_parser.add_argument(
        "dump_id",
        metavar="DUMP_ID",
        type=str,
        help="Dump ID to delete.",
    )

    # ---------------- GET INFO ----------------
    info_parser = subparsers.add_parser(
        "get-info",
        help="Show dump information",
        description="Display detailed information about a dump.",
    )

    info_parser.add_argument(
        "dump_id",
        metavar="DUMP_ID",
        type=str,
        help="Dump ID.",
    )

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
