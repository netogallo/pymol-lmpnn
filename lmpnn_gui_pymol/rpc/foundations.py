import re
from typing import Awaitable, Optional

class Transport():

    def _read_line(self) -> Awaitable[str]:
        """
        The rpc protocol organizes messages in a line by line fashion.
        Each line must contain a json object and each json object
        is a single message.

        The transport will read messages line-by-line and handle
        them accordingly
        """
        raise NotImplementedError

PORT_MAGIC_STRING = "lmpnn_gui listening on port"
PORT_MATCH_RE = re.compile(f"{PORT_MAGIC_STRING}\\s*:\\s*(?<PORT>(\\d+))")

def mk_port_magic_string(port: int):
    return f"{PORT_MAGIC_STRING}: {port}\n"

def find_port(text: str) -> Optional[int]:

    match = PORT_MATCH_RE.search(text)

    if match is not None:
        return int(match.group('PORT'))

    
