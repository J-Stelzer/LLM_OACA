import os
import sys
import PyQt6.QtWidgets as qw
import unpaywall as upw
import doi_lookup as doi
import numpy as np
import pandas as pd
from db import Database
import re

from llm_communicator import LLMCommunicator
import chat_gpt
import claude
import gemini

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
        paragraph_label = qw.QLabel("Enter source reference and paragraph:")
        source_text = qw.QTextEdit()
        source_text.setPlaceholderText("Enter source reference for the paragraph.")
        source_text.setMaximumHeight(50)
        paragraph_text_field = qw.QTextEdit()
        paragraph_text_field.setPlaceholderText("Sample paragraph with citations [1] and [2].")
        paragraph_layout.addWidget(paragraph_label)
        paragraph_layout.addWidget(source_text)
        paragraph_layout.addWidget(paragraph_text_field)
        return paragraph_layout

    @staticmethod
    def add_citations_section():
        citation_layout = qw.QVBoxLayout()
        citations_label = qw.QLabel("Enter citations:")

        citations_text_field = qw.QTextEdit()
        citations_text_field.setPlaceholderText("Enter citations.")
        citation_layout.addWidget(citations_label)
        citation_layout.addWidget(citations_text_field)
        return citation_layout

    def on_paper_submit(self, paragraph_layout, citations_layout):


        source_ref = paragraph_layout.itemAt(1).widget().toPlainText()
        if not source_ref.strip():
            self.send_error_message("Please enter a source reference.")
            return

        paragraph = paragraph_layout.itemAt(2).widget().toPlainText().replace("\n", " ")
        if not paragraph.strip():
            self.send_error_message("Please enter a paragraph.")
            return

        citations = citations_layout.itemAt(1).widget().toPlainText()
        if not citations.strip():
            self.send_error_message("Please enter citations.")
            return

        cit_pro = CitationProcessor()
        ref = [cit_pro.split_citation(source_ref)]
        ref = cit_pro.get_citation_infos(ref, True)
        if not ref:
            self.send_error_message("Error occurred. Please check your source reference input.")
            return
        ref_id = cit_pro.save_citation(ref[0])

        # print(citations.strip().split("\n"))
        cits = list(cit_pro.split_citations(citations))
        #print(cits)
        citation_infos = cit_pro.get_citation_infos(cits)
        if not citation_infos:
            self.send_error_message("Error occurred. Please check your citation input.")
            return

        cit_ids = cit_pro.save_citations(citation_infos)
        para_id = cit_pro.save_paragraph(paragraph, ref_id)

        cit_pro.save_reference_citation_links(ref_id, cit_ids)


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


    def get_paragraph_options(self):
        db = Database()
        sources = db.get_sources()
        options = []
        for source in sources:
            options.append(source["Title"])
        return options


    def generate_new_citations(self, llm_choice, paper_choices):
        papers = []
        db = Database()
        try:
            for paper in paper_choices:
                source = db.get_paper_by_title(paper)
                if source:
                    ref_count = db.get_citation_count(source["_id"])
                    paragraph = db.get_paragraph_by_source_id(source["_id"])['Paragraph']
                    papers.append({
                        "Title": source["Title"],
                        "DOI": source["DOI"],
                        "Paragraph": paragraph,
                        "Count": ref_count
                    })
        except Exception as e:
            print(f"Error retrieving paper information: {e}")
            self.send_error_message("Error retrieving paper information. Please check the database connection and data integrity.")
            return
        try:
            for llm in llm_choice:
                for paper in papers:
                    query = f"Generate {paper['Count']} citations for the following paragraph: {paper['Paragraph']}"
                    if llm == "ChatGPT":
                        communicator = chat_gpt.ChatGPT()
                    elif llm == "Claude":
                        communicator = claude.Claude()
                    elif llm == "Gemini":
                        communicator = gemini.Gemini()
                    else:
                        communicator = LLMCommunicator()
                        # communicator = perplexity.Perplexity()
                    response = communicator.generate_response(query)
                    print(response)
                    cit_pro = CitationProcessor()

                    print(f"Generated citations for {paper['Title']} using {llm}: {response}")

        except Exception as e:
            print(f"Error generating citations: {e}")
            self.send_error_message("Error generating citations. Please check the LLM responses and query formatting.")
            return

    def add_generate_section(self):
        generate_frame = qw.QFrame()
        generate_layout = qw.QVBoxLayout()
        generate_label = qw.QLabel("Generate citations for one or multiple papers:")
        llm_multiple_choice = qw.QListWidget()
        llm_multiple_choice.addItems(["ChatGPT", "Claude", "Gemini", "Perplexity"])
        llm_multiple_choice.setSelectionMode(qw.QAbstractItemView.SelectionMode.MultiSelection)
        paper_selection = qw.QListWidget()
        paper_selection.addItems(self.get_paragraph_options())
        paper_selection.setSelectionMode(qw.QAbstractItemView.SelectionMode.MultiSelection)
        generate_button = qw.QPushButton("Generate Citations")
        generate_button.clicked.connect(lambda: self.generate_new_citations(
            [item.text() for item in llm_multiple_choice.selectedItems()],
            [item.text() for item in paper_selection.selectedItems()]
        ))
        generate_layout.addWidget(generate_label)
        generate_layout.addWidget(llm_multiple_choice)
        generate_layout.addWidget(paper_selection)
        generate_layout.addWidget(generate_button)
        generate_frame.setLayout(generate_layout)
        return generate_frame



    def create_central_widget(self):
        central_widget = qw.QTabWidget()

        central_widget.addTab(self.add_paper_section(), "Add Paragraph")
        central_widget.addTab(self.add_generate_section(), "Generate Citations")

        self.setCentralWidget(central_widget)

    def open_file(self):
        print("Open file action triggered")

    def save_file(self):
        print("Save file action triggered")

    def open_preferences(self):
        print("Open preferences action triggered")



class CitationProcessor:
    def __init__(self):
        pass


    def split_citations(self, citations):
        cits = citations.strip().split("\n")
        for cit in cits:
            yield self.split_citation(cit)

    def split_citation(self, citation):
        full_citation = citation
        # use a regex to split the title ( [A-Za-z ]{15,}\. )
        title_match = re.search(r"\. [A-Za-z ]{15,}\.", citation)
        title = title_match.group(0).strip(' .').strip('. ') if title_match else "Unknown"
        return {
            "full_citation": full_citation,
            "title": title
        }

    def lookup_doi(self, citation, title):
        doi_lookup = doi.DOILookup()
        result = doi_lookup.lookup(citation, title)
        return result

    def lookup_unpaywall(self, dois):
        upw_lookup = upw.Unpaywall()
        result = upw_lookup.lookup(dois)
        return result

    def get_citation_infos(self, citations, source = False):
        try:
            citation_infos = []
            dois = []
            for citation in citations:
                full_citation = citation["full_citation"]
                title = citation["title"]
                doi_result = self.lookup_doi(citation, title)
                if doi_result:
                    dois.append(doi_result[0]["DOI"])

            unpaywall_results = self.lookup_unpaywall(dois)
            print(unpaywall_results)
            # this is a pd dataframe, we need to iterate over the rows
            for index, row in unpaywall_results.iterrows():
                result = row.to_dict()
                print(result)
                if result:
                    authors = []
                    for author in result["z_authors"]:
                        authors.append(author["raw_author_name"])
                    print(authors)
                    citation_infos.append({
                        "DOI": result["doi"],
                        "Title": result["title"],
                        "Authors": authors,
                        "Journal": result["journal_name"],
                        "Published": result["published_date"],
                        "Open Access": result["is_oa"],
                        "OA Standard": result["oa_status"],
                        "URL": result["doi_url"],
                        "Source": source
                    })

            #print(citation_infos)
            return citation_infos
        except Exception as e:
            print(f"Error during citation info retrieval: {e}")
            return None

    def save_citations(self, citations):
        db = Database()
        return db.insert_papers(citations)

    def save_citation(self, citation):
        db = Database()
        return db.insert_paper(citation)

    def save_reference_citation_links(self, ref_id, cit_ids):
        # Ref_id is the id of the source paper, cit_ids is a list of ids of the cited papers
        db = Database()
        links = [{"SourceID": ref_id, "CitationID": cit_id} for cit_id in cit_ids]
        return db.insert_references(links)

    def save_paragraph(self, paragraph, source_id):
        db = Database()
        return db.insert_paragraph({
            "Paragraph": paragraph,
            "SourceID": source_id,
        })

    def process_generated_citations(self, generated_citations):
        processed_citations = []
        for citation in generated_citations:
            processed_citation = self.split_citation(citation)
            processed_citations.append(processed_citation)
        return processed_citations

if __name__ == "__main__":
    app = qw.QApplication(sys.argv)
    window = MainWindow()

    sys.exit(app.exec())


