import time
from typing import List

from dumptool.clients.dbus_client import DBusClient
from dumptool.models import DumpInfo, DumpType


class DumpWaitTimeout(RuntimeError):
    """A dump did not reach a terminal state within the requested timeout."""


class DumpService:
    def __init__(self):
        self.client = DBusClient()

    def list_dumps(self) -> List[DumpInfo]:
        dumps = self.client.list_dumps()
        return [self.client.get_dump_info(d.object_path) for d in dumps]

    def create_dump(
        self,
        dump_type: DumpType,
        error_log_id=None,
        failing_unit_id=None,
    ) -> str:
        return self.client.create_dump(
            dump_type,
            error_log_id,
            failing_unit_id,
        )

    def delete_dump(self, dump_id: str) -> bool:
        dumps = self.client.list_dumps()
        dump = next((d for d in dumps if d.id == dump_id), None)

        if not dump:
            raise ValueError(f"Dump ID {dump_id} not found")

        return self.client.delete_dump(dump.object_path)

    def get_dump_info(self, dump_id: str) -> DumpInfo:
        dumps = self.client.list_dumps()

        dump = next((d for d in dumps if d.id == dump_id), None)

        if not dump:
            raise ValueError(f"Dump ID {dump_id} not found")

        return self.client.get_dump_info(dump.object_path)

    def wait_for_dump(
        self,
        dump_id: str,
        timeout: float,
        poll_interval: float = 1.0,
        object_path=None,
    ) -> DumpInfo:
        deadline = time.monotonic() + timeout

        if object_path is None:
            dumps = self.client.list_dumps()
            dump = next(
                (entry for entry in dumps if entry.id == dump_id), None
            )
            if not dump:
                raise ValueError(f"Dump ID {dump_id} not found")
            object_path = dump.object_path

        while True:
            info = self.client.get_dump_info(object_path)
            if info.is_terminal:
                return info

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                unit = "second" if timeout == 1 else "seconds"
                raise DumpWaitTimeout(
                    f"Dump {dump_id} did not complete within"
                    f" {timeout:g} {unit}"
                )

            time.sleep(min(poll_interval, remaining))
