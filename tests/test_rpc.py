import asyncio
from asyncio import CancelledError, TaskGroup
from enum import Enum
from pytest import mark
from pytest_asyncio import fixture
from typing import Any, AsyncIterator, Awaitable, Callable, Coroutine, List, NamedTuple, TypeVar, Union

from lmpnn_gui_pymol.shared.log import default_logger, Logger
from lmpnn_gui_pymol.shared.rpc.run import MessageDispatcher, MessageDispatcherException, TransactionDispatcher, TxId, run_tcp_client, run_tcp_server

pytestmark = mark.asyncio(loop_scope="module")

class DummyTransactionDispatcher(TransactionDispatcher):

    class _Message(MessageDispatcher):

        def __init__(self, dispatcher: 'DummyTransactionDispatcher', uid: TxId):
            super().__init__()
            self.__logger = dispatcher.__logger.new_scope(_class = '_Message')
            self.__dispatcher = dispatcher

        def on_message(self, payload: dict) -> Awaitable[None]:
            return self.__dispatcher.__incomming.put(payload)

        async def on_error(self, exn: MessageDispatcherException) -> None:
            await self.__dispatcher.__incomming.put(exn)

        async def __aiter__(self) -> AsyncIterator[dict]:
            self.__logger.log_debug("Beging send loop")

            try:
                while(True):
                    yield await self.__dispatcher.__outgoing.get()
                    self.__logger.log_debug("Sending message")
            except CancelledError:
                self.__logger.log_debug("End send loop")

    def __init__(self, logger: Logger):
        super().__init__()
        self.__incomming: asyncio.Queue[Union[dict, Exception]] = asyncio.Queue()
        self.__outgoing: asyncio.Queue[dict] = asyncio.Queue()
        self.__logger = logger

    def begin_transaction(self, transaction_id: int) -> MessageDispatcher:
        return self._Message(self, transaction_id)

    async def receive(self):

        value = await self.__incomming.get()

        if isinstance(value, Exception):
            raise value
        else:
            return value

    async def send(self, value: dict):
        await self.__outgoing.put(value)

class TerminateTaskGroupException(Exception):

    @classmethod
    def terminate(cls, group: TaskGroup) -> None:

        async def kill():
            raise cls()

        group.create_task(kill())

class TaskGroupFixtureTimeoutException(Exception):

    @classmethod
    async def with_timeout(cls, timeout: int) -> None:

        await asyncio.sleep(timeout)
        print("killing due to timeout")
        raise cls()

class TaskGroupFixture:
    class State(Enum):
        INIT = 1
        RUNNING = 2
        DONE = 3

    def __init__(self):
        self.__init_tasks: List[Coroutine[Any, Any, Any]] = []
        self.__state = self.State.INIT
        self.__task_group = asyncio.TaskGroup()

    def __assert_not_done(self):
        if self.__state == self.State.DONE:
            raise Exception("The TaskGroupFixture instance has exited.")

    def create_task(self, coro: Coroutine[Any, Any, Any]) -> None:
        self.__assert_not_done()

        if self.__state == self.State.INIT:
            self.__init_tasks.append(coro)
        else:
            self.__task_group.create_task(coro)

    def with_timeout(self, timeout: int) -> None:
        self.create_task(TaskGroupFixtureTimeoutException.with_timeout(timeout))

    async def __aenter__(self, *args, **kwargs) -> TaskGroup:
        tg = await self.__task_group.__aenter__(*args, **kwargs)
        for task in self.__init_tasks:
            tg.create_task(task)

        return tg

    async def __aexit__(self, *args, **kwargs) -> None:
        await self.__task_group.__aexit__(*args, **kwargs)

@fixture(scope='function')
async def task_group() -> TaskGroupFixture:
    group = TaskGroupFixture()
    group.with_timeout(5)
    return group

class DummyChannels(NamedTuple):
    client: DummyTransactionDispatcher
    server: DummyTransactionDispatcher

@fixture
async def testing_logger() -> Logger:
    logger = default_logger()
    return logger.new_scope(role = 'testing_logger')

@fixture
async def tcp_channels(testing_logger: Logger, task_group: TaskGroupFixture):
    client_dispatcher = DummyTransactionDispatcher(testing_logger.new_scope(dispatcher_type = 'client'))
    server_dispatcher = DummyTransactionDispatcher(testing_logger.new_scope(dispatcher_type = 'server'))

    async def run_client():
        await asyncio.sleep(1)
        await run_tcp_client(
            dispatcher = client_dispatcher,
            logger = testing_logger.new_scope(socket_type = 'client')
        )

    async def run_server():
        await run_tcp_server(
            dispatcher = server_dispatcher,
            logger = testing_logger.new_scope(socket_type = 'server')
        )

    task_group.create_task(run_server())
    task_group.create_task(run_client())
    return DummyChannels(client_dispatcher, server_dispatcher)

@mark.asyncio
async def test_rpc(task_group: TaskGroupFixture, tcp_channels: DummyChannels):

    async with task_group as tg:
        (client, server) = tcp_channels
        await client.send({'x': 42})
        result = await server.receive()

