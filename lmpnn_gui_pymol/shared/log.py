from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Dict, NamedTuple, Union

class LogSeverity(Enum):
    Error = 0
    Warning = 1
    Info = 2
    Debug = 3

class LogAttributes(NamedTuple):
    """
    Class meant to represent contextual attributes that are to be logged
    alongside the main log. While each logger is free to use theese attributes
    however it likes, the abstract logging classes provide the semantics to
    manage the current scope of attributes and also supply the set of attributes
    to the class that ultimately writes the logs.
    """
    attributes: Dict[str, str]

    def union(self, other: Union[Dict[str, str], 'LogAttributes']) -> 'LogAttributes':

        if len(other) == 0:
            return self

        new_scope = {}

        for k,v in self.attributes.items():
            new_scope[k] = v

        if isinstance(other, LogAttributes):
            other = other.attributes

        for k,v in other.items():
            new_scope[k] = v

        return LogAttributes(attributes = new_scope)

class Logger(metaclass=ABCMeta):

    def __init__(self, scope : Union[LogAttributes, Dict[str, str]] = {}):
        self.__counters: Dict[str, int] = {}

        if isinstance(scope, dict):
            scope = LogAttributes(attributes = scope)
        self.__scope = scope

    @abstractmethod
    def __log__(self, message: str, scope: LogAttributes, log_type: LogSeverity):
        """
        This method must be overriden to create a concrete logging implementation.
        It will be called every time a message is logged with all the context
        associated to that log. It is responsible for converting the log message
        and context into the corresponding format and writing that value to
        the logging channel.
        """
        raise NotImplementedError

    @abstractmethod
    def __new_scope__(self, scope: LogAttributes) -> 'Logger':
        raise NotImplementedError

    def log(self, message: str, log_type=LogSeverity.Info, **attributes: str):
        self.__log__(
            message,
            self.__scope.union(attributes),
            log_type
        )

    def new_scope(self, **kwargs: str) -> 'Logger':
        return self.__new_scope__(self.__scope.union(kwargs))

    def log_debug(self, message: str, **kwargs: str):
        self.log(message, log_type=LogSeverity.Debug, **kwargs)

    def log_warning(self, message: str, **attributes: str) -> None:
        self.log(
            message,
            log_type = LogSeverity.Warning,
            **attributes
        )

    def log_error(self, message: Union[Exception,str]):

        if isinstance(message, Exception):
            message = str(message)
        self.log(message, log_type=LogSeverity.Error)

    def log_count(self, tag: str, log_type=LogSeverity.Info, **kwargs: str):

        if tag not in self.__counters:
            self.__counters[tag] = 0
        self.__counters[tag] += 1
        count = self.__counters[tag]

        self.log(
            f"{tag}",
            log_type=log_type,
            count = str(count),
            **kwargs
        )
