import asyncio
from socket import create_connection, socket
from typing import Awaitable

from .foundations import Transport

class TcpClientTransport(Transport):

    def __init__(self, port, host='127.0.0.1'):
        self.__host = host
        self.__port = port
        self.__socket = None

    async def __get_socket(self) -> socket:

        if self.__socket is None:
            self.__socket = await asyncio.to_thread(
                lambda: create_connection((self.__host, self.__port))
            )

        return self.__socket

    async def _read_line(self) -> str:

        sock = await self.__get_socket()
        return ""
