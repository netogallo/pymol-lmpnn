import asyncio
from asyncio import CancelledError, TaskGroup
from pytest import mark
from pytest_asyncio import fixture
from typing import AsyncIterator, Awaitable, NamedTuple, Union

from lmpnn_gui_pymol.shared.log import default_logger, Logger
from lmpnn_gui_pymol.shared.rpc.run import MessageDispatcher, MessageDispatcherException, TransactionDispatcher, run_tcp_client, run_tcp_server

pytestmark = mark.asyncio(loop_scope="module")


class DummyTransactionDispatcher(TransactionDispatcher, MessageDispatcher):

    def __init__(self, logger: Logger):
        super().__init__()
        self.__incomming: asyncio.Queue[Union[dict, Exception]] = asyncio.Queue()
        self.__outgoing: asyncio.Queue[dict] = asyncio.Queue()
        self.__logger = logger

    def on_message(self, payload: dict) -> Awaitable[None]:
        return self.__incomming.put(payload)

    async def on_error(self, exn: MessageDispatcherException) -> None:
        await self.__incomming.put(exn)

    def begin_transaction(self, transaction_id: int) -> MessageDispatcher:
        return self

    async def receive(self):

        value = await self.__incomming.get()

        if isinstance(value, Exception):
            raise value
        else:
            return value

    async def send(self, value: dict):
        await self.__outgoing.put(value)

    async def __aiter__(self) -> AsyncIterator[dict]:
        self.__logger.log_debug("Beging send loop")

        try:
            while(True):
                yield await self.__outgoing.get()
                self.__logger.log_debug("Sending message")
        except CancelledError:
            self.__logger.log_debug("End send loop")

class TerminateTaskGroupException(Exception):

    @classmethod
    def terminate(cls, group: TaskGroup) -> None:

        async def kill():
            raise cls()

        group.create_task(kill())

@fixture
async def task_group():

    try:
        async with asyncio.TaskGroup() as group:
            yield group
            TerminateTaskGroupException.terminate(group)
    except TerminateTaskGroupException:
        pass

class DummyChannels(NamedTuple):
    client: DummyTransactionDispatcher
    server: DummyTransactionDispatcher

@fixture
async def tcp_channels(task_group: TaskGroup):
    client_dispatcher = DummyTransactionDispatcher(default_logger())
    server_dispatcher = DummyTransactionDispatcher(default_logger())

    async def run_client():
        await run_tcp_client(dispatcher = client_dispatcher)

    async def run_server():
        await run_tcp_server(dispatcher = server_dispatcher)

    task_group.create_task(run_server())
    await asyncio.sleep(1)
    task_group.create_task(run_client())
    return DummyChannels(client_dispatcher, server_dispatcher)

@mark.asyncio
async def test_rpc(tcp_channels: DummyChannels):
    (client, server) = tcp_channels
    await client.send({'x': 42})
    result = await server.receive()

