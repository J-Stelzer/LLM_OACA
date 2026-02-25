import os
import sys
import PyQt6.QtWidgets as qw
from PyQt6.QtWidgets import QTextEdit
import unpaywall as upw
import doi_lookup as doi
import numpy as np
import pandas as pd
from db import Database

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

        cits = [cit.strip() for cit in citations.split("\n") if cit.strip()]
        citation_infos = self.get_citation_infos(cits)
        if not citation_infos:
            self.send_error_message("No valid citations found. Please check your input.")
            return

        self.save_citations(citation_infos)
        qw.QMessageBox.information(self, "Success", "Paragraph and citations saved successfully!")

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
        central_widget.addTab(qw.QPushButton("Generate Citations"), "Generate Citations")

        self.setCentralWidget(central_widget)

    def open_file(self):
        print("Open file action triggered")

    def save_file(self):
        print("Save file action triggered")

    def open_preferences(self):
        print("Open preferences action triggered")


    def lookup_doi(self, citation):
        doi_lookup = doi.DOILookup()
        result = doi_lookup.lookup(citation)
        return result

    def lookup_unpaywall(self, dois):
        upw_lookup = upw.Unpaywall()
        result = upw_lookup.lookup(dois)
        return result

    def get_citation_infos(self, citations):
        citation_infos = []
        dois = []
        for citation in citations:
            doi_result = self.lookup_doi(citation)
            if doi_result:
                dois.append(doi_result[0]["DOI"])

        unpaywall_results = self.lookup_unpaywall(dois)
        for result in unpaywall_results:
            if result:
                citation_infos.append({
                    "DOI": result.get("doi"),
                    "Title": result.get("title"),
                    "Authors": result.get("authors"),
                    "Journal": result.get("journal_name"),
                    "Year": result.get("year"),
                    "Open Access": result.get("is_oa"),
                    "OA Standard": result.get("oa_status"),
                    "URL": result.get("url_for_pdf") if result.get("is_oa") else None
                })

        return citation_infos

    @staticmethod
    def save_citations(citations):
        db = Database()
        db.insert_papers(citations)



if __name__ == "__main__":
    app = qw.QApplication(sys.argv)
    window = MainWindow()

    sys.exit(app.exec())


