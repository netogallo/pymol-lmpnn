from asyncio import Task
import asyncio
from typing import NamedTuple, Set

from .foundations import Envelope, parse, Transport, TransportClosedException
from ..log import Logger

class MessageContext(NamedTuple):
    """
    The transport from which the message
    originated.
    """
    transport: Transport

    """
    The raw message in string form
    """
    message: str

class TransportEntry(NamedTuple):
    uid : str
    transport : Transport
    pending : Set[Task[str]]

    async def __read_line(self) -> str:
        return await self.transport._read_line()

    def task(self) -> Task[str]:
        """
        Obtain a task that waits for a line to be produced
        by the transport. A task from the queue is returned
        if any, otherwise a new task is created.
        """
        if len(self.pending) > 0:
            return self.pending.pop()

        return Task(self.__read_line())

    def add_task_to_queue(self, task: Task[str]):
        """
        Add a task to the queue of tasks corresponding to
        this transport. If the task is already in the queue,
        this function is a nop.
        """
        if task not in self.pending:
            self.pending.add(task)

class TransportManager:

    def __init__(self):
        self.__transports : Set[TransportEntry] = set()

    async def _read_line(self) -> MessageContext:
        """
        Read a line from the first transport that has a line
        available.
        """

        pending_tasks = {
            entry.task(): entry
            for entry in self.__transports
        }

        (next_tasks,still_pending) = await asyncio.wait(
            pending_tasks.keys(),
            return_when = asyncio.FIRST_COMPLETED
        )

        # For each transport, we will spwan a request and
        # keep it until that request completes. Therefore
        # me must keep track of all tasks that are still
        # pending.
        for task, entry in pending_tasks.items():
            if task in still_pending:
                entry.add_task_to_queue(task)

        assert len(next_tasks) == 1, "Logical error, next task should only contain one item"
        completed_task = next_tasks.pop()
        completed_task_entry = pending_tasks[completed_task]

        try:
            return MessageContext(
                completed_task_entry.transport,
                completed_task.result()
            )
        except TransportClosedException:
            # If the transport has been closed, we remove it
            # from our set of transports and retry
            self.__transports.remove(completed_task_entry)
            return await self._read_line()

class Dispatcher:

    def __init__(
        self,
        logger: Logger,
        transport: Transport
    ):
        self.__transport = transport
        self.__logger = logger.new_scope(f"Dispatcher[{transport.id()}]")

    async def main_loop_async(self):
        async for raw_message in self.__transport:

            self.__logger.log_count("handling message")
            self.__logger.log_debug(f"payload: {raw_message}")

            envelope = parse(Envelope, raw_message)

