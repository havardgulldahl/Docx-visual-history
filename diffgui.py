import os
import subprocess
import sys
from difflib import ndiff, unified_diff

import docx
import openai
import requests
from O365 import Account, FileSystemTokenBackend
from O365.sharepoint import Site
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def convert_docx_to_md_with_pandoc(file_path):
    try:
        process = subprocess.run(
            ["pandoc", "-f", "docx", "-t", "markdown", file_path],
            capture_output=True,
            text=True,
            check=True,
        )
        return process.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Pandoc failed or is not installed, use python-docx as a fallback
        return convert_docx_to_text(file_path)


def convert_docx_to_text(file_path):
    doc = docx.Document(file_path)
    full_text = [paragraph.text for paragraph in doc.paragraphs]
    return "\n".join(full_text)


def compare_documents(file1, file2):
    if file1.endswith(".docx") and file2.endswith(".docx"):
        text1 = convert_docx_to_md_with_pandoc(file1)
        text2 = convert_docx_to_md_with_pandoc(file2)
    else:
        with open(file1, "r", encoding="utf-8") as f1, open(
            file2, "r", encoding="utf-8"
        ) as f2:
            text1 = f1.read()
            text2 = f2.read()

    diff = ndiff(text1.splitlines(), text2.splitlines())
    return diff


class DiffViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Microsoft 365 Word text edits visualised")
        self.setGeometry(100, 100, 1000, 700)

        # Main layout
        mainLayout = QHBoxLayout()

        # Left layout for file loading and diff viewer
        leftLayout = QVBoxLayout()

        # Text edit for showing the diff
        self.diffViewer = QTextEdit(self)
        self.diffViewer.setReadOnly(True)

        # Buttons to load files
        self.loadFile1Button = QPushButton("Load File 1", self)
        self.loadFile2Button = QPushButton("Load File 2", self)

        self.loadFile1Button.clicked.connect(lambda: self.loadFile(1))
        self.loadFile2Button.clicked.connect(lambda: self.loadFile(2))

        leftLayout.addWidget(self.loadFile1Button)
        leftLayout.addWidget(self.loadFile2Button)
        leftLayout.addWidget(self.diffViewer)

        # Right layout for summary
        rightLayout = QVBoxLayout()
        self.summaryViewer = QTextEdit(self)
        self.summaryViewer.setReadOnly(True)
        rightLayout.addWidget(self.summaryViewer)

        # Add layouts to main layout
        mainLayout.addLayout(leftLayout)
        mainLayout.addLayout(rightLayout)

        # Central Widget
        centralWidget = QWidget()
        centralWidget.setLayout(mainLayout)
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
                diff = compare_documents(self.file1, self.file2)
                self.displayDiff(diff)

                # Generate and display summary
                summary = self.generate_summary(diff)

            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"An error occurred while reading the files: {e}"
                )
                # raise

    def displayDiff(self, diff):
        self.diffViewer.clear()
        for line in diff:
            color = QColor("#000000")  # Default to black
            if line.startswith("+"):
                color = QColor("#007F00")  # Softer green
            elif line.startswith("-"):
                color = QColor("#7F0000")  # Softer red

            self.diffViewer.setTextColor(color)
            self.diffViewer.append(line.strip())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def generate_summary(self, diff):
        # Convert diff to a string
        diff_text = "\n".join(diff)

        # Construct a prompt for ChatGPT
        prompt = f"Explain the following code changes in simple terms:\n\n{diff_text}"

        client = openai.OpenAI()

        prompt = (
            f"I have two versions of a code segment with some changes. Below is the diff output between the original and modified versions. "
            f"Please provide a concise summary explaining the changes in simple terms, highlighting any added, removed, or altered functionality.\n\n"
        )

        stream = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": diff_text},
            ],
            stream=True,
        )
        for chunk in stream:
            print(chunk.choices[0].delta.content or "", end="")
            self.diffViewer.append(chunk.choices[0].delta.content)


class MicrosoftGraphClient:
    def __init__(self, client_id, client_secret, redirect_uri, site_url):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.site_url = site_url

        # Initialize token backend and account
        self.token_backend = FileSystemTokenBackend(
            token_path=".", token_filename="o365_token.txt"
        )
        self.account = self._get_authenticated_account()

    def _get_authenticated_account(self):
        account = Account(
            (self.client_id, self.client_secret), token_backend=self.token_backend
        )
        if not account.is_authenticated:
            auth_url, _ = account.get_authorization_url(redirect_uri=self.redirect_uri)
            print("Please visit this URL to authenticate:", auth_url)
            auth_code = input("Enter the auth code: ")
            account.get_access_token(auth_code, redirect_uri=self.redirect_uri)
        return account

    def get_file_version_history(self, file_path):
        site = Site(
            self.site_url, auth_flow_type="credential", auth_account=self.account
        )

        # Get the file and its version history
        file = site.get_item(file_path)
        print("File Name:", file.display_name)
        print("File ID:", file.id)

        version_history = requests.get(
            f"{self.site_url}/_api/web/GetFileByServerRelativeUrl('{file_path}')/Versions",
            headers={"Authorization": f"Bearer {self.account.access_token}"},
        )
        versions = version_history.json()["value"]

        print("Version History:")
        for version in versions:
            print(
                f"Version: {version['VersionLabel']}, Modified by: {version['CreatedBy']['Email']}, Modified on: {version['Created']}"
            )


# Example usage
if __name__ == "__main__":
    client_id = os.environ.get("CLIENT_ID")
    client_secret = os.environ.get("CLIENT_SECRET")
    redirect_uri = os.environ.get("REDIRECT_URI")
    site_url = os.environ.get("SITE_URL")
    file_path = os.environ.get("FILE_PATH")

    graph_client = MicrosoftGraphClient(
        client_id, client_secret, redirect_uri, site_url
    )
    graph_client.get_file_version_history(file_path)

    app = QApplication(sys.argv)
    mainWin = DiffViewer()
    mainWin.show()
    sys.exit(app.exec_())
