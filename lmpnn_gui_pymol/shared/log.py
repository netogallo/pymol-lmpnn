from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Dict

class LogSeverity(Enum):
    Error = 0
    Info = 1
    Debug = 2

class Logger(metaclass=ABCMeta):

    def __init__(self):
        self.__counters: Dict[str, int] = {}

    @abstractmethod
    def log(self, message: str, log_type=LogSeverity.Info):
        raise NotImplementedError

    def new_scope(self, scope_name: str) -> 'Logger':
        raise NotImplementedError

    def log_debug(self, message: str):
        self.log(message, log_type=LogSeverity.Debug)

    def log_error(self, message: str):
        self.log(message, log_type=LogSeverity.Error)

    def log_count(self, tag: str, log_type=LogSeverity.Info):

        if tag not in self.__counters:
            self.__counters[tag] = 0
        self.__counters[tag] += 1
        count = self.__counters[tag]

        self.log(f"{tag}[{count}]", log_type=log_type)
