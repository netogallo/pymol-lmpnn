import sys
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QTextEdit
from PyQt5.QtCore import QProcess

install_info = """
Welcome to LMPNN GUI

This plugin requries additional components to run. They can be
automatically installed by pression "Start Installation".

The initial installation will take several minutes. Subsequent
updates should be much faster.

This text box will display the installation logs. If you run
into issues. You can provide these logs to help the team
diagnose your issue.
"""

class Installer(QDialog):
    def __init__(
        self,
        script : str
    ):
        super().__init__()

        self.setWindowTitle("LMPNN Gui Installer")
        self.resize(600, 400)

        self.layout = QVBoxLayout(self)

        self.output_box = QTextEdit(self)
        self.output_box.setReadOnly(True)

        self.run_button = QPushButton("Start/Retry Installation", self)
        self.run_button.clicked.connect(self.run_command)

        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.clicked.connect(self.cancel_command)

        self.layout.addWidget(self.output_box)
        self.layout.addWidget(self.run_button)
        self.layout.addWidget(self.cancel_button)

        self.script = script
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)

    def run_command(self):
        self.output_box.clear()

        # This must be called before restarting the
        # process. No harm if called when process
        # hasen't started
        self.process.waitForFinished()
        self.process.start(
            sys.executable,
            ["-u", self.script]
        )
        print(f"started script {self.script}")
        self.run_button.setEnabled(False)

    def __del__(self):
        self.process.kill()

    def cancel_command(self):
        self.process.kill()
        self.process.waitForFinished()
        self.reject()

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        self.output_box.append(str(data, encoding='utf-8'))

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        self.output_box.append(str(data, encoding='utf-8'))

    def process_finished(self, exit_code: int, exit_status: int):

        self.run_button.setEnabled(True)
        if exit_code == 0:
            self.accept()
        else:
            self.output_box.append("Installation failed!")

    def try_install(self) -> bool:
        return self.exec() == QDialog.DialogCode.Accepted

