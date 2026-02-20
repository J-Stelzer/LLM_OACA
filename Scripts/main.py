import os
import sys
import PyQt6.QtWidgets as qw
from PyQt6.QtWidgets import QTextEdit

CITATION_STYLES = ["MLA", "APA", "Chicago", "Harvard", "Vancouver"]


class MainWindow(qw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OACA API Tool")
        self.setGeometry(250,100, 750, 750)

        self.create_menus()
        self.create_central_widget()

        self.show()


    def create_menus(self):
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction("Exit", self.close)
        edit_menu = self.menuBar().addMenu("Edit")
        edit_menu.addAction("Preferences", self.open_preferences)


    def send_error_message(self, message):
        qw.QMessageBox.critical(self, "Error", message)

    @staticmethod
    def add_paragraph_section():
        paragraph_layout = qw.QVBoxLayout()
        paragraph_label = qw.QLabel("Enter paragraph:")
        paragraph_text_field = qw.QTextEdit()
        paragraph_text_field.setPlaceholderText("Sample paragraph with citations [1] and [2].")
        paragraph_layout.addWidget(paragraph_label)
        paragraph_layout.addWidget(paragraph_text_field)
        return paragraph_layout

    @staticmethod
    def get_citation_radio_buttons():
        for style in CITATION_STYLES:
            radio_button = qw.QRadioButton(style)
            yield radio_button


    @staticmethod
    def add_citations_section():
        citation_layout = qw.QVBoxLayout()
        citations_label = qw.QLabel("Select citation style and enter citations:")
        radio_layout = qw.QHBoxLayout()
        for radio_button in MainWindow.get_citation_radio_buttons():
            radio_layout.addWidget(radio_button)

        citations_text_field = qw.QTextEdit()
        citations_text_field.setPlaceholderText("Select citation style above and enter citations.")
        citation_layout.addWidget(citations_label)
        citation_layout.addLayout(radio_layout)
        citation_layout.addWidget(citations_text_field)
        return citation_layout

    def on_paper_submit(self, paragraph_layout, citations_layout):
        paragraph = paragraph_layout.itemAt(1).widget().toPlainText()
        if not paragraph.strip():
            self.send_error_message("Please enter a paragraph.")
            return

        citations = citations_layout.itemAt(2).widget().toPlainText()
        if not citations.strip():
            self.send_error_message("Please enter citations.")
            return
        
        style = None
        for i in range(citations_layout.itemAt(1).layout().count()):
            radio_button = citations_layout.itemAt(1).layout().itemAt(i).widget()
            if radio_button.isChecked():
                style = radio_button.text()
                break
        if style is None:
            self.send_error_message("Please select a citation style.")
            return
        print("Citation style:", style)
        print("Paragraph:", paragraph)
        print("Citations:", citations)

    def add_paper_section(self):
        paper_frame = qw.QFrame()
        paper_layout = qw.QVBoxLayout()
        paper_layout.addLayout(self.add_paragraph_section())
        paper_layout.addLayout(self.add_citations_section())
        print(paper_layout.itemAt(0).layout().itemAt(1).widget())
        paper_submit = qw.QPushButton("Add Paragraph and Citations")
        paper_submit.clicked.connect(lambda:
                                     self.on_paper_submit(
                                         paper_layout.itemAt(0).layout(),
                                         paper_layout.itemAt(1).layout()
                                     )
        )
        paper_layout.addWidget(paper_submit)
        paper_frame.setLayout(paper_layout)
        return paper_frame



    def create_central_widget(self):
        central_widget = qw.QTabWidget()

        central_widget.addTab(self.add_paper_section(), "Add Paragraph")
        central_widget.addTab(qw.QPushButton("GenerateCitations"), "Generate Citations")

        self.setCentralWidget(central_widget)

    def open_file(self):
        print("Open file action triggered")

    def save_file(self):
        print("Save file action triggered")

    def open_preferences(self):
        print("Open preferences action triggered")




if __name__ == "__main__":
    app = qw.QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())