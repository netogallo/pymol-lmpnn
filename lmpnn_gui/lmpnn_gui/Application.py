from PyQt5.QtCore import pyqtProperty, pyqtSignal, QObject
from PyQt5.QtQuick import QQuickView

class Application(QObject):

    def __init__(self):
        super().__init__()
        self.setProperty('text', 'LMPNN Clicky Pointy')

    @pyqtProperty(str)
    def text(self) -> str:
        return "LMPNN Clicky Pointy"
