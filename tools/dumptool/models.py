from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class DumpType(Enum):
    BMC = "bmc"
    SYSTEM = "system"
    RESOURCE = "resource"
    FAULTLOG = "faultlog"

    # IBM dump types
    HOSTBOOT = "hostboot"
    HARDWARE = "hardware"
    SBE = "sbe"

    @property
    def object_path(self) -> str:
        if self in (
            DumpType.HOSTBOOT,
            DumpType.HARDWARE,
            DumpType.SBE,
        ):
            return "/xyz/openbmc_project/dump/system"

        return f"/xyz/openbmc_project/dump/{self.value}"

    @staticmethod
    def from_path(path: str):
        if "/dump/bmc/" in path:
            return DumpType.BMC
        elif "/dump/system/" in path:
            return DumpType.SYSTEM
        elif "/dump/resource/" in path:
            return DumpType.RESOURCE
        elif "/dump/faultlog/" in path:
            return DumpType.FAULTLOG
        else:
            raise ValueError("Unknown dump type")


@dataclass(frozen=True)
class DumpCreateSpec:
    dbus_type: Optional[str]
    requires_error_log_id: bool = False
    requires_failing_unit_id: bool = False


DUMP_CREATE_SPECS: Dict[DumpType, DumpCreateSpec] = {
    DumpType.BMC: DumpCreateSpec(dbus_type=None),
    DumpType.HOSTBOOT: DumpCreateSpec(
        dbus_type="Hostboot",
        requires_error_log_id=True,
    ),
    DumpType.HARDWARE: DumpCreateSpec(
        dbus_type="Hardware",
        requires_error_log_id=True,
        requires_failing_unit_id=True,
    ),
    DumpType.SBE: DumpCreateSpec(
        dbus_type="SBE",
        requires_error_log_id=True,
        requires_failing_unit_id=True,
    ),
}


def validate_create_parameters(
    dump_type: DumpType,
    error_log_id: Optional[int],
    failing_unit_id: Optional[int],
) -> None:
    """Validate a dump request against the dump manager contract."""
    spec = DUMP_CREATE_SPECS.get(dump_type)
    if spec is None:
        raise ValueError(
            f"Dump type '{dump_type.value}' cannot be created by dumptool"
        )

    if spec.requires_error_log_id and error_log_id is None:
        raise ValueError(f"{dump_type.value} dump requires --error-id")

    if spec.requires_failing_unit_id and failing_unit_id is None:
        raise ValueError(f"{dump_type.value} dump requires --failing-id")

    if not spec.requires_error_log_id and error_log_id is not None:
        raise ValueError(f"{dump_type.value} dump does not accept --error-id")

    if not spec.requires_failing_unit_id and failing_unit_id is not None:
        raise ValueError(f"{dump_type.value} dump does not accept --failing-id")

    max_uint64 = (1 << 64) - 1
    for option, value in (
        ("--error-id", error_log_id),
        ("--failing-id", failing_unit_id),
    ):
        if value is not None and not 0 <= value <= max_uint64:
            raise ValueError(f"{option} must be between 0 and {max_uint64}")


@dataclass
class DumpEntry:
    id: str
    type: DumpType
    object_path: str


@dataclass
class DumpInfo:
    id: str
    type: DumpType

    # Actual subtype determined from IBM D-Bus interface
    subtype: Optional[str] = None

    size: Optional[int] = None
    completed: Optional[bool] = None
    offloaded: Optional[bool] = None
    started_time: Optional[str] = None
    ended_time: Optional[str] = None

    @property
    def final_type(self):
        if self.subtype:
            return self.subtype
        return self.type.value

    @property
    def size_kb(self):
        return f"{self.size // 1024} KB" if self.size else "-"

    @property
    def status(self):
        if self.completed is None:
            return "Unknown"
        return "Completed" if self.completed else "In Progress"
