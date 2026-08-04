from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import numpy as np
import pandas as pd

from keys import DB_KEY

uri = DB_KEY

class Database:
    def __init__(self):
        self.client = MongoClient(uri, server_api=ServerApi('1'))
        self.db = self.client["oaca"]


    def insert_paper(self, paper_data):
        """
        Saves a single paper into the database
        :param paper_data: A dictionary containing the paper data to be saved
        :return: The ID of the inserted paper
        """
        collection = self.db["papers"]
        result = collection.insert_one(paper_data)
        return result.inserted_id


    def insert_papers(self, papers_data):
        """
        Saves multiple papers into the database
        :param papers_data: A list of dictionaries, each containing the data of a paper to be saved
        :return: The IDs of the inserted papers
        """
        collection = self.db["papers"]
        result = collection.insert_many(papers_data)
        return result.inserted_ids


    def get_source_papers(self):
        """
        Retrieves all source papers from the database
        :return: A list of source papers
        """
        collection = self.db["papers"]
        papers = list(collection.find({"Source": True}))
        return papers


    def insert_paragraph(self, paragraph_data):
        """
        Saves a single paragraph into the database
        :param paragraph_data: A dictionary containing the paragraph data to be saved
        :return: The ID of the inserted paragraph
        """
        collection = self.db["paragraphs"]
        result = collection.insert_one(paragraph_data)
        return result.inserted_id


    def insert_references(self, references_data):
        """
        Saves multiple references into the database
        :param references_data: A list of dictionaries, each containing the data of a reference to be saved
        :return: The IDs of the inserted references
        """
        collection = self.db["references"]
        result = collection.insert_many(references_data)
        return result.inserted_ids


    def get_citation_count(self, source_id):
        """
        Retrieves the citation count for the given source_id
        :param source_id: The ID of the source paper
        :return: The number of citations for the source paper
        """
        collection = self.db["references"]
        count = collection.count_documents({"SourceID": source_id})
        return count


    def get_sources(self):
        """
        Retrieves all source papers from the database
        :return: A list of all source papers
        """
        collection = self.db["papers"]
        sources = list(collection.find({"Source": True}))
        return sources

    def get_existing_sources(self, source_ref):
        """
        Returns a list of all source papers whose reference is equal to the given source_ref
        :param source_ref: The reference to search for (can be a DOI or a URL)
        :return: A list of source papers matching the given reference
        """
        collection = self.db["papers"]
        sources = list(collection.find({"$or": [{"DOI": source_ref}, {"URL": source_ref}], "Source": True}))
        return sources


    def get_missing_doi_papers(self):
        """
        Retrieves all papers from the database that have a missing DOI (i.e. DOI is null or None)
        :return: A list of papers with missing DOIs
        """
        collection = self.db["papers"]
        papers = list(collection.find({"DOI": {"$exists": True, "$eq": None}}))
        return papers


    def update_missing_doi_papers(self, papers):
        """
        Updates papers whose DOI is null or None
        :param papers:  A list of dictionaries, each containing the data of a paper to be updated
        :return: None
        """
        collection = self.db["papers"]
        for paper in papers:
            collection.update_one({"_id": paper["_id"]}, {"$set": {"DOI": paper["DOI"]}})


    def get_unknown_authors(self):
        """
        Retrieves all authors from the database
        :return: a list of papers with unknown authors
        """
        collection = self.db["papers"]
        authors = list(collection.find({"Authors": ['Unknown']}))
        return authors


    def get_missing_cit_count(self):
        """
        Retrieves all papers from the database that have a missing citation count (i.e. Citation Count is 0)
        :return: A list of papers with missing citation counts
        """
        collection = self.db["papers"]
        papers = list(collection.find({"$and": [{"DOI": {'$exists': True}}, {"Citation Count": 0}]}))
        return papers


    def update_missing_authors(self, papers):
        """
        Updates papers whose authors are null or None
        :param papers: a list of dictionaries, each containing the data of a paper to be updated
        :return: None
        """
        collection = self.db["papers"]
        # set the author to null, change type of DOI to string and set the new DOI
        for paper in papers:
            collection.update_one({"_id": paper["_id"]}, {"$set": {"Authors": paper["Authors"], "DOI": str(paper["DOI"])}})


    def get_missing_information_papers(self):
        """
        Retrieves all papers from the database that have a missing information (indicated by DOI or authors)
        :return: a list of papers with missing information
        """
        collection = self.db["papers"]
        papers = list(collection.find({"$and": [{"DOI": {"$exists": True}}, {"Authors": {"$exists": True, "$eq": None}}]}))
        return papers


    def update_missing_information_papers(self, papers):
        """
        Updates papers whose authors are null or None
        :param papers: a list of dictionaries, each containing the data of a paper to be updated
        :return: None
        """
        collection = self.db["papers"]
        for paper in papers:
            collection.update_one({"_id": paper["_id"]},
                                  {"$set":
                                       {"DOI": str(paper["DOI"]),
                                        "Authors": paper["Authors"],
                                        "Title": str(paper["Title"]),
                                        "Journal": str(paper["Journal"]),
                                        "Published": str(paper["Published"]),
                                        "Open Access": bool(paper["Open Access"]),
                                        "OA Standard": str(paper["OA Standard"]),
                                        "URL": str(paper["URL"])
                                       }
                                   })


    def update_citation_count(self, paper_id, count):
        """
        Updates the citation count for a given paper
        :param paper_id: The ID of the paper to update
        :param count: The new citation count
        :return: None
        """
        collection = self.db["papers"]
        collection.update_one({"_id": paper_id}, {"$set": {"Citation Count": count}})


    def get_paper_by_doi(self, doi):
        """
        Retrieves a single paper from the database based on DOI
        :param doi: The DOI of the paper
        :return: The paper matching the given DOI, or None if no such paper exists
        """
        collection = self.db["papers"]
        paper = collection.find_one({"DOI": doi})
        return paper


    def get_source_paper_by_title(self, title):
        """
        Retrieves a single paper from the database based on Title
        :param title: The title of the paper
        :return: The paper matching the given title, or None if no such paper exists
        """
        collection = self.db["papers"]
        paper = collection.find_one({"Title": title, "Source": True})
        return paper


    def get_source_paper_by_id(self, paper_id):
        """
        Retrieves a single paper from the database based on ID
        :param paper_id: The ID of the paper
        :return: The paper matching the given ID, or None if no such paper exists
        """
        collection = self.db["papers"]
        paper = collection.find_one({"_id": paper_id, "Source": True})
        return paper


    def get_paragraph_by_source_id(self, source_id):
        """
        Retrieves a single paragraph from the database based on SourceID
        :param source_id: The SourceID of the paragraph
        :return: The paragraph matching the given SourceID, or None if no such paragraph exists
        """
        collection = self.db["paragraphs"]
        paragraph = collection.find_one({"SourceID": source_id})
        return paragraph


    def insert__all_input_data(self, source_data, paragraph_data, citations_data):
        """
        Saves all input data to the database
        :param source_data: A dictionary containing the source paper data to be saved
        :param paragraph_data: A dictionary containing the paragraph data to be saved
        :param citations_data: A list of dictionaries containing the citation data to be saved
        :return: The IDs of the inserted documents
        """
        source_id = self.insert_paper(source_data)
        paragraph_id = self.insert_paragraph({**paragraph_data, "SourceID": source_id})
        citation_ids = self.insert_papers(citations_data)
        self.insert_references([{"SourceID": source_id, "CitationID": cit_id} for cit_id in citation_ids])
        return source_id, paragraph_id, citation_ids


    def insert_generated(self, generated_citations_data):
        """
        Inserts generated citations data into the database
        :param generated_citations_data: A list of dictionaries containing the generated citation data to be saved
        :return: The IDs of the inserted documents
        """
        collection = self.db["generated"]
        result = collection.insert_many(generated_citations_data)
        return result.inserted_ids


    def get_all_ref_papers(self):
        """
        Retrieves all references from the database
        :return: A DataFrame containing all reference papers
        """
        collection = self.db["papers"]
        papers = pd.DataFrame(collection.find({"Source": False, "DOI": {"$exists": True}}))
        return papers


    def get_all_ref_papers_grouped_by_source(self):
        """
        Retrieves all references from the database and groups them by their source paper
        :return: A DataFrame containing all reference papers grouped by their source paper
        """
        collection = self.db["papers"]
        papers = pd.DataFrame(collection.find({"Source": False}))
        reference_ids = papers["_id"].tolist()
        collection2 = self.db["references"]
        source_ids = pd.DataFrame(collection2.find({"CitationID": {"$in": reference_ids}}))
        papers = papers.merge(source_ids, left_on="_id", right_on="CitationID")
        grouped = papers.groupby("SourceID").apply(lambda x: x.to_dict(orient="records"))
        return grouped


    def get_all_gen_papers_grouped_by_source_and_llm(self, iteration = 0):
        """
        Retrieves all references from the database and groups them by their source paper
        :return: A DataFrame containing all generated papers grouped by their source paper and the LLM used for generation
        """
        collection = self.db["generated"]
        papers = pd.DataFrame(collection.find({"Iteration": iteration}))
        grouped = papers.groupby(["SourceID", "LLM"]).apply(lambda x: x.to_dict(orient="records"))
        return grouped


    def get_double_generation_papers(self, llm):
        """
        Retrieves all generated papers from the database, where the source paper has been used multiple times to generate citations
        These can be found by looking at the Iteration field; If there are papers with Iteration = 1(+),
        get the ID of the source paper and get all generated papers with the same source paper ID
        :return: a DataFrame containing all generated papers grouped by their source paper and the LLM used for generation,
                where the source paper has been used multiple times to generate citations
        """
        collection = self.db["generated"]
        papers = pd.DataFrame(collection.find({"Iteration": {"$gt": 0}}))
        source_ids = papers["SourceID"].unique().tolist()
        papers = pd.DataFrame(collection.find({"SourceID": {"$in": source_ids}, "LLM": llm}))
        grouped = papers.groupby(["SourceID"]).apply(lambda x: x.to_dict(orient="records"))
        return grouped


    def update_paragraph_info(self, paragraph):
        """
        Updates the paragraph information in the database
        :param paragraph: A dictionary containing the paragraph data to be updated, including the "_id" field to identify the paragraph
        :return: None
        """
        collection = self.db["paragraphs"]
        collection.update_one({"_id": paragraph["_id"]}, {"$set": {"Paragraph": paragraph["Paragraph"]}})
