import asyncio
from socketserver import TCPServer
from typing import Awaitable, NamedTuple, Optional

from ..log import default_logger, Logger

from .foundations import AsyncCounter, MessageDispatcher, MessageDispatcherException, TransactionDispatcher, TxId
from .dispatcher import Dispatcher
from .tcp import TcpClientTransport, StreamTransport

def run_tcp_client(
    dispatcher: TransactionDispatcher,
    port: int = 16666,
    host = '127.0.0.1',
    logger: Optional[Logger] = None
) -> Awaitable[None]:
    logger = default_logger() if logger is None else logger
    logger.log_debug("Starting tcp client")
    return Dispatcher(
        logger = logger,
        transport = TcpClientTransport(logger, port, host = host),
        dispatcher = dispatcher
    ).main_loop_async()

async def run_tcp_server(
    dispatcher: TransactionDispatcher,
    port: int = 16666,
    host = '127.0.0.1',
    logger: Optional[Logger] = None
) -> None:

    connections = AsyncCounter()
    legit_logger = default_logger() if logger is None else logger
    legit_logger.log_debug("Starting TCP server")

    async def handler(reader, writer):
        nonlocal connections
        nonlocal legit_logger
        uid = await connections.next()
        legit_logger.log_debug("Accepted TCP connection")
        await Dispatcher(
            logger = legit_logger,
            transport = StreamTransport(f"uid={uid}", legit_logger, reader, writer),
            dispatcher = dispatcher
        ).main_loop_async()


    server = await asyncio.start_server(
        handler,
        host,
        port
    )

    async def run_server():
        nonlocal server
        async with server:
            await server.serve_forever()

    try:
        await asyncio.to_thread(run_server)
    except Exception as e:
        legit_logger.log_debug("Caught exception. Terminating server.")
        server.close()
        raise e
