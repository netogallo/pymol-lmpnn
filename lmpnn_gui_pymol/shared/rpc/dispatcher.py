from asyncio import CancelledError, Task, TaskGroup
import asyncio
from typing import Awaitable, Dict, NamedTuple, Optional, Set

from .foundations import *
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
    logger: Logger

class Dispatcher:

    def __init__(
        self,
        logger: Logger,
        transport: Transport,
        dispatcher: TransactionDispatcher
    ):
        self.__transport = transport
        self.__logger = logger.new_scope(
            class_name = "Dispatcher",
            transport = transport.id()
        )
        self.__transaction_dispatcher = dispatcher
        self.__message_dispatchers: Dict[int, MessageDispatcherEntry] = {}
        self.__message_id_counter = AsyncCounter()

    def __new_message_id(self) -> Awaitable[int]:
        return self.__message_id_counter.next()

    async def __transport_write_line(
        self,
        dispatcher: MessageDispatcher,
        msg: Envelope,
        logger: Optional[Logger] = None
    ) -> bool:

        if logger is None:
            logger = self.__logger

        write_error = None

        try:
            # Try serializing and writing message to transport
            await self.__transport._write_line(serialize(Envelope, msg))
        except Exception as e:

            # Something went wrong while serializing and writing
            # to transport
            logger.log_error(e)
            write_error = e

        if write_error is None:
            # No error happened. Return control
            # Indicate caller that execution can
            # continue
            return True

        try:
            # An error occured. We now attempt to notify the
            # dispatcher and subsequently terminate the dispatcher
            await dispatcher.on_error(MessageDispatcherResponseSerializationException(write_error))
        except Exception as e:
            logger.log_error(e)

        # Notify caller that execution should be stopped
        return False

    async def __handle_responses(
        self,
        transaction_id: int,
        dispatcher: MessageDispatcher,
        logger: Logger
    ):

        try:
            async for msg in dispatcher:
                logger.log_count(f"replying message")

                envelope = Envelope(
                    message_id = await self.__new_message_id(),
                    transaction_id = transaction_id,
                    transaction_control = TransactionControl.MESSAGE,
                    value = msg
                )
                if not (await self.__transport_write_line(dispatcher, envelope, logger = logger)):
                    # An error occured while serializing to transport. Under these circumstances
                    # the iteration is to be stopped
                    return

            # Iterator has completed, notify the other party
            end = Envelope(
                message_id = await self.__new_message_id(),
                transaction_id = transaction_id,
                transaction_control = TransactionControl.END
            )
            await self.__transport_write_line(dispatcher, end, logger = logger)
        except CancelledError:
            # The remote party has cancelled the transaction
            logger.log("Received cancellation. Terminating message response loop.")
        except Exception as e:
            # An unexpected error has occured while reading messages from
            # the dispatcher. This means that no more mesages will be sent
            # to the remote party. Therefore we must end the communication
            logger.log_error(e)
            end = Envelope(
                message_id = await self.__new_message_id(),
                transaction_id = transaction_id,
                transaction_control = TransactionControl.ERROR,
                error = str(e)
            )
            await self.__transport_write_line(dispatcher, end, logger = logger)

    async def __dispatch_error(
        self,
        dispatcher_entry: MessageDispatcherEntry,
        error: Optional[str]
    ) -> None:

        dispatcher = dispatcher_entry.message_dispatcher
        logger = dispatcher_entry.logger
        try:
            exn = MessageDispatcherRemotePartyException(Exception(error))
            await dispatcher.on_error(exn)
            dispatcher_entry.responses_task.cancel()
        except Exception as e:
            logger.log_error(e)

    def __dispatch(self, dispatch_tasks: TaskGroup, msg: Envelope):
        transaction_id = msg.transaction_id
        self.__logger.log_count(f"dispatching message[{transaction_id}]")

        if transaction_id not in self.__message_dispatchers:
            dispatcher = self.__transaction_dispatcher.begin_transaction(transaction_id)
            logger = self.__logger.new_scope(transaction_id = str(transaction_id))
            self.__message_dispatchers[msg.transaction_id] = MessageDispatcherEntry(
                message_dispatcher = dispatcher,
                responses_task = dispatch_tasks.create_task(
                    self.__handle_responses(transaction_id, dispatcher, logger)
                ),
                logger = logger
            )

        dispatcher_entry = self.__message_dispatchers[transaction_id]
        dispatcher = dispatcher_entry.message_dispatcher
        control_code = msg.transaction_control
        value = msg.value
        error = msg.error

        def end_response_loop():
            dispatcher_entry.responses_task.cancel()
            self.__message_dispatchers.pop(transaction_id)

        if control_code == TransactionControl.MESSAGE and value is not None:
            dispatcher.on_message(value)
        elif control_code == TransactionControl.MESSAGE and value is None:
            self.__logger.log_warning(
                "Received message of type 'MESSAGE' without payload.",
                transaction_id = str(transaction_id),
                message_id = str(msg.message_id)
            )
        elif control_code == TransactionControl.ERROR:
            dispatch_tasks.create_task(
                self.__dispatch_error(dispatcher_entry, error)
            )
        elif control_code == TransactionControl.END:
            self.__logger.log("Transaction terminated by remote party. Cancelling response loop.", transaction_id = str(transaction_id))
            end_response_loop()

            if error is not None:
                self.__logger.log_error(f"Remote party terminated with error.", error = str(error))
        else:
            self.__logger.log_warning(
                "Received unknown message. Ignoring.",
                control_code = str(control_code),
                value = str(value),
                error = str(error)
            )

    async def main_loop_async(self):
        async with TaskGroup() as dispatch_task_group:
            async for raw_message in self.__transport:

                self.__logger.log_count("handling message")
                self.__logger.log_debug(f"message payload", payload = raw_message)

                envelope = parse(Envelope, raw_message)
                self.__dispatch(dispatch_task_group, envelope)

