from dataclasses import dataclass
from enum import Enum
from typing import Optional


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
