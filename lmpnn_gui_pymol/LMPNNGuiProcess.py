from enum import Enum
from PyQt5.QtCore import pyqtSlot, QProcess, QProcessEnvironment

from .constants import LMPNN_PYTHON
from .log import Logger
from .rpc.foundations import find_port

class LMPNNGuiProcessState(Enum):
    INIT = 1
    READY = 2

class LMPNNGuiProcess(QProcess):

    def __init__(self, logger: Logger):
        super().__init__()

        self.__logger = logger.new_scope("QProcess.lmpnn_gui")
        self.setProgram(LMPNN_PYTHON)
        self.setArguments(["-u", "-m", "lmpnn_gui"])
        env = QProcessEnvironment.systemEnvironment()
        env.insert("QT_QUICK_BACKEND", "software")
        self.setProcessEnvironment(env)
        self.setProcessChannelMode(QProcess.SeparateChannels)
        self.readyReadStandardOutput.connect(self.__on_stdout)
        self.readyReadStandardError.connect(self.__on_stderr)
        self.__state = LMPNNGuiProcessState.INIT
        self.__init_text = ""

    @pyqtSlot()
    def __on_stdout(self):

        msg = str(self.readAllStandardOutput().data())
        self.__logger.log(msg)

        if self.__state == LMPNNGuiProcessState.INIT:
            self.__on_stdout_init(msg)
    
    def __on_stdout_init(self, msg: str) -> None:
        """
        After the lmpnn_gui process launches, it will start an rpc server
        on an arbitrary tcp port. We must read what port is being used from
        the standard input. To do so, we accumulate all the output that
        has occured so far and search for the port.
        """

        self.__init_text += msg

        port = find_port(self.__init_text)

        if port is not None:
            self.__transition_to_ready(port)


    def __transition_to_ready(self, port: int) -> None:

        self.__init_text = ""
        self.__state = LMPNNGuiProcessState.READY

    @pyqtSlot()
    def __on_stderr(self):
        pass

