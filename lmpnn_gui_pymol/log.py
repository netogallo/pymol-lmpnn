from enum import Enum

class LogSeverity(Enum):
    Info = 1
    Error = 2

class Logger():

    def log(self, message: str, log_type=LogSeverity.Info):
        raise NotImplementedError

    def new_scope(self, scope_name: str) -> 'Logger':
        raise NotImplementedError
