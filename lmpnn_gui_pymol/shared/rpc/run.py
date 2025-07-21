import asyncio
from typing import Awaitable, Optional

from ..log import default_logger, Logger

from .foundations import AsyncCounter, MessageDispatcher, MessageDispatcherException, TransactionDispatcher
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
    m_logger: Optional[Logger] = None
) -> None:

    connections = AsyncCounter()
    logger: Logger = default_logger() if m_logger is None else m_logger
    logger.log_debug("Starting TCP server")

    async def handler(reader, writer):
        nonlocal connections
        nonlocal logger
        uid = await connections.next()
        logger.log_debug("Accepted TCP connection")
        await Dispatcher(
            logger = logger,
            transport = StreamTransport(f"uid={uid}", logger, reader, writer),
            dispatcher = dispatcher
        ).main_loop_async()

    server = await asyncio.start_server(
        handler,
        host,
        port
    )

    async with server:
        await server.serve_forever()


