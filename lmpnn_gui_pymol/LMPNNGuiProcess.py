from PyQt5.QtCore import QProcess, QProcessEnvironment

from .constants import LMPNN_PYTHON

class LMPNNGuiProcess(QProcess):

    def __init__(self):
        super().__init__()

        self.setProgram(LMPNN_PYTHON)
        self.setArguments(["-u", "-m", "lmpnn_gui"])
        env = QProcessEnvironment.systemEnvironment()
        env.insert("QT_QUICK_BACKEND", "software")
        self.setProcessEnvironment(env)

