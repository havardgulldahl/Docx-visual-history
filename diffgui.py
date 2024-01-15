import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QMessageBox,
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

from difflib import ndiff


class DiffViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Diff Viewer")
        self.setGeometry(100, 100, 800, 600)

        # Text edit for showing the diff
        self.diffViewer = QTextEdit(self)
        self.diffViewer.setReadOnly(True)

        # Buttons to load files
        self.loadFile1Button = QPushButton("Load File 1", self)
        self.loadFile2Button = QPushButton("Load File 2", self)

        self.loadFile1Button.clicked.connect(lambda: self.loadFile(1))
        self.loadFile2Button.clicked.connect(lambda: self.loadFile(2))

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.loadFile1Button)
        layout.addWidget(self.loadFile2Button)
        layout.addWidget(self.diffViewer)

        # Central Widget
        centralWidget = QWidget()
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)

        # File paths
        self.file1 = None
        self.file2 = None

    def loadFile(self, file_number):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File")
        if file_name:
            if file_number == 1:
                self.file1 = file_name
            else:
                self.file2 = file_name

            self.compareFiles()

    def compareFiles(self):
        if self.file1 and self.file2:
            try:
                with open(self.file1, "r") as file1, open(self.file2, "r") as file2:
                    file1_lines = file1.readlines()
                    file2_lines = file2.readlines()

                diff = ndiff(file1_lines, file2_lines)
                self.displayDiff(diff)
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"An error occurred while reading the files: {e}"
                )

    def displayDiff(self, diff):
        self.diffViewer.clear()
        for line in diff:
            color = QColor(Qt.black)
            if line.startswith("+"):
                color = QColor(Qt.green)
            elif line.startswith("-"):
                color = QColor(Qt.red)
            elif line.startswith("?"):
                color = QColor(Qt.blue)

            self.diffViewer.setTextColor(color)
            self.diffViewer.append(line.strip())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = DiffViewer()
    mainWin.show()
    sys.exit(app.exec_())
