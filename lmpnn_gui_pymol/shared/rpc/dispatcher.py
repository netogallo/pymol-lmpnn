from asyncio import CancelledError, Task
import asyncio
from typing import Dict, NamedTuple, Set

from .foundations import Envelope, MessageDispatcher, parse, Transport, TransactionControl, TransactionDispatcher, TransportClosedException
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

class MessageDispatcherEntry(NamedTuple):
    message_dispatcher: MessageDispatcher
    responses_task: Task[None]

class Dispatcher:

    def __init__(
        self,
        logger: Logger,
        transport: Transport,
        dispatcher: TransactionDispatcher
    ):
        self.__transport = transport
        self.__logger = logger.new_scope(f"Dispatcher[{transport.id()}]")
        self.__transaction_dispatcher = dispatcher
        self.__message_dispatchers: Dict[int, MessageDispatcherEntry] = {}

    async def __handle_responses(self, transaction_id: int, dispatcher: MessageDispatcher):

        try:
            async for msg in dispatcher:
                self.__logger.log_count(f"replying message[{transaction_id}]")
                # todo: transport needs to be made aware of the reply
        except CancelledError:
            # The remote party has cancelled the transaction
            self.__logger.log(f"Terminating the message response loop for {transaction_id}")

    def __dispatch(self, msg: Envelope):
        loop = asyncio.get_event_loop()
        transaction_id = msg.transaction_id
        self.__logger.log_count(f"dispatching message[{transaction_id}]")

        if transaction_id not in self.__message_dispatchers:
            dispatcher = self.__transaction_dispatcher.begin_transaction(transaction_id)
            self.__message_dispatchers[msg.transaction_id] = MessageDispatcherEntry(
                message_dispatcher = dispatcher,
                responses_task = loop.create_task(self.__handle_responses(transaction_id, dispatcher))
            )

        dispatcher_entry = self.__message_dispatchers[transaction_id]
        dispatcher = dispatcher_entry.message_dispatcher
        control_code = msg.transaction_control
        value = msg.value

        if control_code == TransactionControl.MESSAGE and value is not None:
            dispatcher.on_message(value)
        if control_code == TransactionControl.MESSAGE and value is None:
            self.__logger.log_error(f"The message {msg.message_id} of transaction {transaction_id} has control code 'MESSAGE' but empty payload.")
        if control_code == TransactionControl.END:
            self.__logger.log(f"The transaction {transaction_id} has been terminated by the remote party, cancelling responses")
            dispatcher_entry.responses_task.cancel()
            self.__message_dispatchers.pop(transaction_id)

    async def main_loop_async(self):
        async for raw_message in self.__transport:

            self.__logger.log_count("handling message")
            self.__logger.log_debug(f"payload: {raw_message}")

            envelope = parse(Envelope, raw_message)
            self.__dispatch(envelope)

