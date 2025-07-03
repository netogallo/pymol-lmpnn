from abc import abstractmethod
from asyncio import StreamReader, StreamWriter
import asyncio
from typing import Awaitable, Tuple

from .foundations import Transport

class StreamTransportBase(Transport):

    @abstractmethod
    def _open(self) -> Awaitable[Tuple[StreamReader, StreamWriter]]:
        raise NotImplementedError

    async def __get_reader(self) -> StreamReader:
        (reader,_) = await self._open()
        return reader

    async def _read_line(self) -> str:

        # Todo: Connection is currently local, so
        # unlikely to fail, but reeconnect mechanism
        # should be added
        reader = await self.__get_reader()
        return (await reader.readline()).decode()

class TcpClientTransport(StreamTransportBase):

    def __init__(self, port, host='127.0.0.1'):
        self.__host = host
        self.__port = port
        self.__stream = None

    def id(self) -> str:
        return f"type=tcp_client,host={self.__host},port={self.__port}"

    async def _open(self) -> Tuple[StreamReader, StreamWriter]:

        if self.__stream is None:
            self.__stream = await asyncio.open_connection(self.__host, self.__port)

        return self.__stream

class StreamTransport(StreamTransportBase):

    def __init__(
        self,
        id: str,
        reader: StreamReader,
        writer: StreamWriter
    ):
        self.__id = id
        self.__reader = reader
        self.__writer = writer

    def id(self) -> str:
        return self.__id

    async def _open(self) -> Tuple[StreamReader, StreamWriter]:
        return (self.__reader, self.__writer)
