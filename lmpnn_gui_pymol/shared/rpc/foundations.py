from abc import ABCMeta, abstractmethod
import asyncio
from enum import Enum
import json
import re
from typing import Any, AsyncIterator, Awaitable, cast, Generic, NamedTuple, Optional, Tuple, Type, TypeVar, Union
import typing

from ..type import TypeChecks

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

    @abstractmethod
    def _write_line(self, line: str) -> Awaitable[None]:
        """
        The rpc protocol sends messages on a line by line fashion. Each
        line is a json encoded object. However, the transport only needs
        to provide a mechanism to write the line to the other party.
        """
        raise NotImplementedError

    async def __aiter__(self) -> AsyncIterator[str]:
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

def all_matching_types(ty: Type) -> tuple[Type,...]:
    origin = typing.get_origin(ty)

    if origin == Union:
        all_types = typing.get_args(ty)
    else:
        all_types = (ty,)

    # Sanity checks. Not all python types are allowed
    # as they cannot be unambigously distinguished
    nt_count = 0
    enum_and_int_count = 0

    for ty in all_types:

        if TypeChecks.is_named_tuple(ty):
            nt_count += 1

        if TypeChecks.is_list(ty) and len(all_types) > 1:
            raise TypeError(f"List cannot appear in a union. Found {ty}.")

        if ty == int or ty == str or issubclass(ty, Enum):
            enum_and_int_count += 1

        if nt_count > 1:
            raise TypeError(f"The union {ty} has more than one NamedTuple. This is ambigous")

        if enum_and_int_count > 1:
            raise TypeError(f"The union {ty} has more than one Enum or int. This is ambigous")

    return all_types

def parse(ty: Type[ParseType], raw: Union[str, dict]) -> ParseType:

    if isinstance(raw, str):
        msg = json.loads(raw)
    else:
        # Copy the dictionary so it can be manipulated
        # w/o altering the input
        msg = dict(**raw)

    def parse_internal(value: Any, field_ty_all: Type) -> Any:
        success = False
        for field_ty in all_matching_types(field_ty_all):

            if TypeChecks.is_any(field_ty):
                raise TypeError(f"The type 'Any' is not supported for parsing/serialization. Found in {field_ty_all}.")

            # Check if type derives from NamedTuple,
            # recursively construct the object if so
            elif TypeChecks.is_named_tuple(field_ty) and isinstance(value, dict):
                return parse(field_ty, value)

            # Check if type is an Enum. In the affirmative
            # case, we attempt re-constructing the enum
            # from the value
            elif issubclass(field_ty, Enum) and isinstance(value, int):
                return field_ty(value)

            # None of the conversion rules applies to this
            # member, just check that the types match
            elif not isinstance(value, field_ty):
                value_type = value.__class__
                raise TypeError(f"The field {name} must have type {field_ty}. Found {value_type}.")

        if not success:
            raise TypeError(f"The field {name} of type {field_ty_all} cannot be parsed.")

    for name,field_ty_all in ty.__annotations__.items():
        # Check that the values in the json dict correspond
        # to the expected values in the tuple's fields. This

        if name not in msg:
            continue

        value = msg[name]
        list_ty = TypeChecks.get_generic_list_type(field_ty_all)

        if list_ty is not None and isinstance(list, value):
            msg[name] = [parse_internal(v, list_ty) for v in value]
        elif list_ty is not None:
            raise TypeError(f"Expecting {value} to be a list")
        else:
            msg[name] = parse_internal(value, field_ty_all)

    msg_any = cast(Any, msg)
    ty_any = cast(Any, ty)
    return ty_any(**msg_any)

def serialize(ty: Type[ParseType], value_to_serialize: ParseType) -> dict:

    result = {}
    for name, field_ty_all in ty.__annotations__.items():

        value = getattr(value_to_serialize, name)

        for field_ty in all_matching_types(field_ty_all):

            # If the field is a Namedtuple, we serialize recursively
            if is_named_tuple(field_ty) and isinstance(value, field_ty):
                result[name] = serialize(field_ty, value)
                break


class TransactionControl(Enum):
    MESSAGE = 1
    END = 2
    ERROR = 3

class Envelope(NamedTuple):
    """
    All messages are wrapped inside an envelope. The envelop contains additional
    metadata which allows identifying and grouping messages sent at different
    times.

    Attributes:
        message_id (int): An identifier that uniquely identifies this message.
        transaction_id (int): The transaction identifier, multiple messages can
            share the same transaction identifier and they will be handled
            within the same context.
        transaction_control (TransactionControl): This field contains control 
            codes that will be used by the message dispatcher to alter the
            state of the communication channel. Note that if the control
            is anything other than MESSAGE, it will be assumed that value
            is None.
        value (dict): The payload. This is the actual content of the message.
    """
    message_id: int
    transaction_id: int
    transaction_control: TransactionControl
    value: Optional[dict] = None
    error: Optional[str] = None

class MessageDispatcherException(Exception):

    def __init__(self, exception: Exception, will_terminate = True):
        super().__init__(exception)
        self.__will_terminate = will_terminate

    @property
    def will_terminate(self) -> bool:
        return self.__will_terminate

class MessageDispatcherRemotePartyException(MessageDispatcherException):
    pass

class MessageDispatcherResponseSerializationException(MessageDispatcherException):
    pass

class MessageDispatcher(metaclass=ABCMeta):
    """
    A message dispatcher is an abstraction that
    provides the logic to have a bi-lateral
    messaage exchange channel between two
    parties.
    """

    @abstractmethod
    def on_message(self, payload: dict) -> None:
        """
        Whenever a message belonging to the transaction
        asociated with this MessageDispatcher is received,
        this method will be called with the message's
        payload as argument.

        It is assumed that this function never throws. If
        a error is to be reported, the iterator should raise
        an execption.
        """
        raise NotImplemented

    @abstractmethod
    def on_error(self, exn: MessageDispatcherException) -> Awaitable[None]:
        """
        This method is used to communicate error conditions to the
        dispatcher. Error conditions include:

        1) The dispatcher's iterator produced a message that cannot
            be serialized.

        2) The remote party reported an error while handling a message
            produced by this dispatcher.

        :param exn: A wrapper value containing the exception and some
            additional contextual information. The class exposes the
            property, 'will_terminate', which advises wether the
            communication will be closed or not after this method
            returns.
        """
        raise NotImplemented

    def __aiter__(self) -> AsyncIterator[dict]:
        """
        This asynchronous iterator is responsible to produce
        the messages that will be sent back to the party
        at the opposite end of the channel. Whenever the
        iterator yields a value, this will be sent back
        to the sender. If the iterator completes, it will
        be assumed that the communication has concluded
        and the bi-lateral channel will be destroyed.
        """
        raise NotImplemented

class TransactionDispatcher(metaclass=ABCMeta):
    """
    This class is responsible for creating a
    MessageDispatcher whenever a new transaction
    is initiated. A transaction represents a
    bilateral channel to exchange messages between
    two parties.
    """

    def begin_transaction(self, transaction_id: int) -> MessageDispatcher:
        """
        If a message with a new transaction_id is received, this method
        will be called to initiate a new bi-lateral message exchange
        between two parties. Ultimately, this is just an abstraction to
        group messages.
        """
        raise NotImplemented

TResource = TypeVar('TResource')

class AsyncResource(Generic[TResource], metaclass=ABCMeta):
    def __init__(self, state: TResource):
        self.__state = state
        self.__lock = asyncio.Lock()

    @abstractmethod
    def __update__(self, state: TResource) -> Awaitable[TResource]:
        raise NotImplementedError

    async def next(self) -> TResource:
        async with self.__lock:
            self.__state = await self.__update__(self.__state)
            return self.__state

class AsyncCounter(AsyncResource[int]):

    def __init__(self, count: int = 0):
        super().__init__(count)

    async def __update__(self, value: int) -> int:
        return value + 1
