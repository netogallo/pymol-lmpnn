import json

class Transport():

    def _read_line(self) -> str:
        """
        The rpc protocol organizes messages in a line by line fashion.
        Each line must contain a json object and each json object
        is a single message.

        The transport will read messages line-by-line and handle
        them accordingly
        """
        raise NotImplementedError
