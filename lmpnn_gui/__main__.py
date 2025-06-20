from os import path
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQuick import QQuickView
import sys

from typing import List

from .Application import Application

def main(argv: List[str]):
    qt = QGuiApplication(argv)

    app = Application()
    app_view = QQuickView()
    app_view.setInitialProperties({'app': app})
    app_view.setSource(QUrl.fromLocalFile(path.join(path.dirname(__file__), "Application.qml")))

    app_view.show()

    return qt.exec()

if __name__ == "__main__":
    main(sys.argv)
