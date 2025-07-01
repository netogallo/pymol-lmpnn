import asyncio
from typing import Tuple

from .foundations import Transport

class TcpClientTransport(Transport):

    def __init__(self, port, host='127.0.0.1'):
        self.__host = host
        self.__port = port
        self.__stream = None

    async def __get_stream(self) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:

        if self.__stream is None:
            self.__stream = await asyncio.open_connection(self.__host, self.__port)

        return self.__stream

    async def __get_reader(self) -> asyncio.StreamReader:
        (reader,_) = await self.__get_stream()
        return reader

    async def _read_line(self) -> str:

        # Todo: Connection is currently local, so
        # unlikely to fail, but reeconnect mechanism
        # should be added
        reader = await self.__get_reader()
        return (await reader.readline()).decode()
