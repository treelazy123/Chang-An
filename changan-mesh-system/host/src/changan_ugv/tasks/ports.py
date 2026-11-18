"""Task boundary: queued transmission is never an execution acknowledgement."""
from dataclasses import dataclass
from typing import Callable, Protocol

@dataclass(frozen=True)
class NodeSnapshot:
    ready: bool = False
    boot_id: str | None = None
    task_types: tuple[str,...] = ()
    execution_mode: str | None = None
    task_operations: tuple[str,...] = ()
    task_id: str | None = None
    task_state: str | None = None

@dataclass(frozen=True)
class SendReceipt:
    queued: bool

class NodeChannel(Protocol):
    def is_connected(self) -> bool: ...
    def snapshot(self,node_id: str) -> NodeSnapshot: ...
    def ready_count(self) -> int: ...
    def send(self,node_id: str,packet: dict) -> SendReceipt: ...

class LocalExecutor(Protocol):
    boot: str
    def handle(self,packet: dict) -> None: ...
    def tick(self,connected: bool) -> None: ...
    def close(self) -> None: ...

ExecutorFactory = Callable[[Callable[[dict],bool], Callable[[],int]], LocalExecutor]
