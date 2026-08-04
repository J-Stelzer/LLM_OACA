import sys
import PyQt6.QtWidgets as qw

from db import Database
import citation_processor as cip
import paragraph_processor as pap
import generation_processor as gep

from llm_communicator import LLMCommunicator
import chat_gpt
import claude
import gemini


class MainWindow(qw.QMainWindow):
    """
    Main application window for the OACA API Tool.
    This class creates the main window, menus, and central widget for the application.
    It provides functionality to add paragraphs and citations, and generate citations using LLMs
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OACA API Tool")
        self.setGeometry(250,100, 750, 750)

        self.create_menus()
        self.create_central_widget()

        self.show()


    def create_menus(self):
        """
        Creates the menu bar with File and Edit menus.
        :return: None
        """
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction("Exit", self.close) # closes window/tool
        edit_menu = self.menuBar().addMenu("Edit")
        edit_menu.addAction("Preferences", self.open_preferences) # not functional


    def send_error_message(self, message):
        """
        Displays an error message in a message box.
        :param message: message to display
        :return: None
        """
        qw.QMessageBox.critical(self, "Error", message)


    @staticmethod
    def add_paragraph_section():
        """
        Creates a layout for the paragraph input section.
        :return: QVBoxLayout
        """
        paragraph_layout = qw.QVBoxLayout()
        paragraph_label = qw.QLabel("Enter source reference and paragraph:")
        source_text = qw.QTextEdit()
        # Field and Label for the source reference
        source_text.setPlaceholderText("Enter source reference for the paragraph.")
        source_text.setMaximumHeight(50)
        # Field and Label for the paragraph
        paragraph_text_field = qw.QTextEdit()
        paragraph_text_field.setPlaceholderText("Sample paragraph with citations [1] and [2].")
        paragraph_layout.addWidget(paragraph_label)
        paragraph_layout.addWidget(source_text)
        paragraph_layout.addWidget(paragraph_text_field)
        return paragraph_layout


    @staticmethod
    def clearInputFields(paragraph_layout, citations_layout):
        """
        Clears the input fields for the paragraph and citations sections.
        :param paragraph_layout: QVBoxLayout for the paragraph input section
        :param citations_layout: QVBoxLayout for the citations input section
        :return: None
        """
        paragraph_layout.itemAt(1).widget().clear()
        paragraph_layout.itemAt(2).widget().clear()
        citations_layout.itemAt(1).widget().clear()


    @staticmethod
    def add_citations_section():
        """
        Creates a layout for the citations input section.
        :return: QVBoxLayout
        """
        # Field and label for reference list
        citation_layout = qw.QVBoxLayout()
        citations_label = qw.QLabel("Enter citations:")

        citations_text_field = qw.QTextEdit()
        citations_text_field.setPlaceholderText("Enter citations.")
        citation_layout.addWidget(citations_label)
        citation_layout.addWidget(citations_text_field)
        return citation_layout


    def on_paper_submit(self, paragraph_layout, citations_layout):
        """
        Handles the submission of a paper, including validation of inputs, processing of citations, and saving to the database.
        :param paragraph_layout: QVBoxLayout for the paragraph input section
        :param citations_layout: QVBoxLayout for the citations input section
        :return: None
        """
        try:
            # Checks if source DOI has been entered
            source_ref = paragraph_layout.itemAt(1).widget().toPlainText()
            if not source_ref.strip():
                self.send_error_message("Please enter a source reference.")
                return

            # Checks if paragraph has been entered
            paragraph = paragraph_layout.itemAt(2).widget().toPlainText().replace("\n", " ")
            if not paragraph.strip():
                self.send_error_message("Please enter a paragraph.")
                return

            # Checks if reference list has been entered
            citations = citations_layout.itemAt(1).widget().toPlainText()
            if not citations.strip():
                self.send_error_message("Please enter citations.")
                return

            # Checks if source paper has already been added to the database
            if self.duplication_check(source_ref):
                qw.QMessageBox.information(self, "Warning", "Paper is already in the database")
                self.clearInputFields(paragraph_layout, citations_layout)
                return
        except Exception as e:
            print(f"Error during verifying citations: {e}")
            return

        # If everything has been entered, the input is being processed
        # First, the paragraph and citations are extracted
        try:
            pro_paragraph, pro_citations = pap.replace_citations_with_indices(paragraph, citations)
            fin_citations = cip.has_apa_dois(pro_citations)
        except Exception as e:
            print(f"Error during citation indexing: {e}")
            return

        # Second, information of the source paper is extracted
        try:
            source = cip.get_apa_dois_from_text(source_ref)
            source = cip.get_citation_infos_from_doi(source)
        except Exception as e:
            print(f"Error during source retrieval: {e}")
            return

        if not source:
            self.send_error_message("Error occurred. Please check your source reference input.")
            return

        # Third, information of the citations is extracted
        try:
            citation_infos = cip.get_citation_infos_from_dois(fin_citations)
        except Exception as e:
            print(f"Error during DOI lookup for citations: {e}")
        #print(cits)
        #citation_infos = cip.get_citation_infos(cits)
        if not citation_infos:
            self.send_error_message("Error occurred. Please check your citation input.")
            return

        # If everything has successfully been extracted and no errors occurred, the information is being saved to the database
        try:
            ref_id = cip.save_citation(source[0])
            cit_ids = cip.save_citations(citation_infos)
            para_id = cip.save_paragraph(pro_paragraph, ref_id, paragraph, citations)
            cip.save_reference_citation_links(ref_id, cit_ids)
            # cip.save_all_input_data(source[0], para_id, cit_ids)
        except Exception as e:
            print(f"Error during data saving process: {e}")
            return

        # Success Message Box is shown
        qw.QMessageBox.information(self, "Success", "Paragraph and citations saved successfully!")
        self.clearInputFields(paragraph_layout, citations_layout)


    def add_paper_section(self):
        """
        Creates a layout for the paper input section, including paragraph and citations sections, and a submit button.
        :return: QFrame containing the paper input layout
        """
        paper_frame = qw.QFrame()
        paper_layout = qw.QVBoxLayout()
        paper_layout.addLayout(self.add_paragraph_section())
        paper_layout.addLayout(self.add_citations_section())
        # print(paper_layout.itemAt(0).layout().itemAt(1).widget())
        # Add submit button
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
        """
        Retrieves the list of paper titles from the database to populate the paper selection list.
        :return: List of paper titles
        """
        db = Database()
        sources = db.get_sources()
        options = []
        for source in sources:
            options.append(source["Title"])
        return options


    def generate_new_citations(self, llm_choice, paper_choices):
        """
        Generates new citations for the selected papers using the specified LLMs.
        :param llm_choice: List of selected LLMs
        :param paper_choices: List of selected papers
        :return: List of generated citation infos
        """
        papers = []
        db = Database()
        try:
            # Iterate over all selected papers and retrieve their information from the database
            for paper in paper_choices:
                source = db.get_source_paper_by_title(paper)
                if source:
                    ref_count = db.get_citation_count(source["_id"])
                    # Quick check to ensure the selected papers have reference papers
                    if ref_count == 0:
                        print(f"Paper '{source['Title']}' has {ref_count} citations.")
                        continue
                    paragraph = db.get_paragraph_by_source_id(source["_id"])['Paragraph']
                    papers.append({
                        "Title": source["Title"],
                        "DOI": source["DOI"],
                        "Paragraph": paragraph,
                        "Count": ref_count,
                        "SourceID": source["_id"]
                    })
        except Exception as e:
            print(f"Error retrieving paper information: {e}")
            self.send_error_message("Error retrieving paper information. Please check the database connection and data integrity.")
            return

        # Iterate over all LLMs; All selected papers are generated for one LLM, then for the next LLM, etc.
        for llm in llm_choice:

            # Iterate over all papers
            for paper in papers:
                try:
                    # Query for the reference generation
                    query = (f"Generate {paper['Count']} references (incl. DOI) for the 'R[Number]' placeholders according to APA standards for the following paragraph: \n\n {paper['Paragraph']} "
                             f"\n\nJust return the references and indication for the placeholder 'R[Number] without any additional text."
                             f"\nIf the reference does not have a DOI, still provide a reference, but indicate 'NO DOI' instead of the DOI/the link")

                    # Select the communicator for the current LLM
                    if llm == "ChatGPT":
                        communicator = chat_gpt.ChatGPT()
                    elif llm == "Claude":
                        communicator = claude.Claude()
                    elif llm == "Gemini":
                        communicator = gemini.Gemini()
                    else:
                        communicator = LLMCommunicator()

                    # Send query to LLM and get response
                    response = communicator.generate_response(query)
                    #print(response)
                    if response is None:
                        continue

                    # Process generated references, starting with splitting them into individual references
                    generated_refs = gep.split_response(response)
                    #print(generated_refs)

                    # Next splits reference into parts (e.g., author, year, title, journal, DOI) and retrieves citation information from the DOIs
                    references = gep.get_reference_parts(generated_refs)
                    #print(references)

                    # Get paper information from the Unpaywall and CrossRef APIs
                    generated_infos = gep.get_citation_infos_from_dois(references)
                    #print(generated_infos)

                    # Save generated papers
                    gep.save_generated_citations(generated_infos, paper["SourceID"], llm)

                    print(f"Generated citations for {paper['Title']} using {llm}: {response}")

                except Exception as e:
                    print(f"Error generating citations: {e}")
                    #self.send_error_message("Error generating citations. Please check the LLM responses and query formatting.")
                    continue


    def add_generate_section(self):
        """
        Creates a layout for the citation generation section, including LLM selection, paper selection, and a generate button.
        :return: QFrame containing the citation generation layout
        """

        # Create folder for citation generation
        generate_frame = qw.QFrame()
        generate_layout = qw.QVBoxLayout()
        generate_label = qw.QLabel("Generate citations for one or multiple papers:")

        # Add selection for LLMs
        llm_multiple_choice = qw.QListWidget()
        llm_multiple_choice.addItems(["ChatGPT", "Claude", "Gemini"]) #, "Perplexity"])
        llm_multiple_choice.setSelectionMode(qw.QAbstractItemView.SelectionMode.MultiSelection)

        # Add selection for papers
        paper_selection = qw.QListWidget()
        paper_selection.addItems(self.get_paragraph_options())
        paper_selection.setSelectionMode(qw.QAbstractItemView.SelectionMode.MultiSelection)

        # Add submission button
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
        """
        Creates the central widget with tabs for adding paragraphs and generating citations.
        :return: QWidget containing the central widget
        """
        central_widget = qw.QTabWidget()

        central_widget.addTab(self.add_paper_section(), "Add Paragraph")
        central_widget.addTab(self.add_generate_section(), "Generate Citations")

        self.setCentralWidget(central_widget)


    def open_file(self):
        # Not functional
        print("Open file action triggered")

    def save_file(self):
        # Not functional
        print("Save file action triggered")

    def open_preferences(self):
        # Not functional
        print("Open preferences action triggered")


    @staticmethod
    def duplication_check(source_ref):
        """
        Checks whether a source paper has already been added to the database
        :param source_ref: DOI of the source paper
        :return: True if the source paper already exists in the database, False otherwise
        """
        db = Database()
        existing_sources = db.get_existing_sources(source_ref)
        return len(existing_sources) > 0


if __name__ == "__main__":
    app = qw.QApplication(sys.argv)
    window = MainWindow()

    sys.exit(app.exec())


