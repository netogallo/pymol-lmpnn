from abc import ABCMeta, abstractmethod
import json
import re
from typing import Any, Awaitable, cast, NamedTuple, Optional, Type, TypeVar, TypeVarTuple, Union

class TransportClosedException(Exception):
    pass

class Transport(metaclass=ABCMeta):

    @abstractmethod
    def id(self) -> str:
        """
        Return a string that identifies this transport.
        """
        raise NotImplementedError

    @abstractmethod
    def _read_line(self) -> Awaitable[str]:
        """
        The rpc protocol organizes messages in a line by line fashion.
        Each line must contain a json object and each json object
        is a single message.

        If the transport has been closed and will no longer produce
        new messages. This function should raise a 'TransportClosedException'
        """
        raise NotImplementedError

    async def __aiter__(self):
        try:
            while(True):
                yield await self._read_line()

        except TransportClosedException:
            pass

PORT_MAGIC_STRING = "lmpnn_gui listening on port"
PORT_MATCH_RE = re.compile(f"{PORT_MAGIC_STRING}\\s*:\\s*(?<PORT>(\\d+))")

def mk_port_magic_string(port: int):
    return f"{PORT_MAGIC_STRING}: {port}\n"

def find_port(text: str) -> Optional[int]:

    match = PORT_MATCH_RE.search(text)

    if match is not None:
        return int(match.group('PORT'))
 
ParseType = TypeVar("ParseType", bound=NamedTuple)

def parse(ty: Type[ParseType], raw: Union[str, dict]) -> ParseType:

    if isinstance(raw, str):
        msg = json.loads(raw)
    else:
        # Copy the dictionary so it can be manipulated
        # w/o altering the input
        msg = dict(**raw)

    for name,field_ty in ty.__annotations__.items():
        # Check that the values in the json dict correspond
        # to the expected values in the tuple's fields. This

        if name not in msg:
            continue

        value = msg[name]

        # Check if type derives from NamedTuple,
        # recursively construct the object if so
        if NamedTuple in field_ty.__orig_bases__:
            msg[name] = parse(field_ty, value)
        elif not isinstance(value, field_ty):
            value_type = value.__class__
            raise TypeError(f"The field {name} must have type {field_ty}. Found {value_type}.")

    msg_any = cast(Any, msg)
    ty_any = cast(Any, ty)
    return ty_any(**msg_any)
