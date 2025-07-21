from abc import abstractmethod
from asyncio import StreamReader, StreamWriter
import asyncio
from typing import Awaitable, Iterable, Optional, Tuple

from .foundations import TransportClosedException, Transport
from ..log import Logger

def encode(line: str) -> bytes:
    if not line.endswith("\n"):
        line = line + "\n"

    return line.encode()

class StreamTransportBase(Transport):

    def __init__(self, logger: Logger):
        self.__logger = logger
        self.__streams: Optional[Tuple[StreamReader,StreamWriter]] = None

    @abstractmethod
    def _open(self) -> Awaitable[Tuple[StreamReader, StreamWriter]]:
        raise NotImplementedError

    async def __get_streams(self) -> Tuple[StreamReader, StreamWriter]:

        result = self.__streams

        if result is None:
            result = await self._open()
            self.__streams = result

        return result

    async def _read_line(self) -> str:

        self.__logger.log_count('_read_line')
        # Todo: Connection is currently local, so
        # unlikely to fail, but reeconnect mechanism
        # should be added
        (reader,_) = await self.__get_streams()

        if reader.at_eof():
            self.__logger.log_debug("End of stream reached. closing.")
            raise TransportClosedException()

        return (await reader.readline()).decode()

    async def _write_lines(self, lines: Iterable[str]) -> None:

        self.__logger.log_count('_write_line')
        (_,writer) = await self.__get_streams()
        writer.writelines(encode(line) for line in lines)
        await writer.drain()

class TcpClientTransport(StreamTransportBase):

    def __init__(self, logger: Logger, port, host='127.0.0.1'):
        super().__init__(
            logger.new_scope(
                _class = 'TcpClientTransport',
                port =  str(port),
                host = host
            )
        )
        self.__host = host
        self.__port = port

    def id(self) -> str:
        return f"type=tcp_client,host={self.__host},port={self.__port}"

    def _open(self) -> Awaitable[Tuple[StreamReader, StreamWriter]]:

        return asyncio.open_connection(self.__host, self.__port)

class StreamTransport(StreamTransportBase):

    def __init__(
        self,
        id: str,
        logger: Logger,
        reader: StreamReader,
        writer: StreamWriter
    ):
        super().__init__(
            logger.new_scope(
                _class = 'StreamTransport',
                id = str(id)
            )
        )
        self.__id = id
        self.__reader = reader
        self.__writer = writer

    def id(self) -> str:
        return self.__id

    async def _open(self) -> Tuple[StreamReader, StreamWriter]:
        return (self.__reader, self.__writer)
