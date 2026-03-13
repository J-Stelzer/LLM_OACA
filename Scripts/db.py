from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from keys import DB_KEY

uri = DB_KEY

class Database:
    def __init__(self):
        self.client = MongoClient(uri, server_api=ServerApi('1'))
        self.db = self.client["oaca"]

    def insert_paper(self, paper_data):
        collection = self.db["papers"]
        result = collection.insert_one(paper_data)
        return result.inserted_id

    def insert_papers(self, papers_data):
        collection = self.db["papers"]
        result = collection.insert_many(papers_data)
        return result.inserted_ids

    def get_source_papers(self):
        collection = self.db["papers"]
        papers = list(collection.find({"Source": True}))
        return papers

    def insert_paragraph(self, paragraph_data):
        collection = self.db["paragraphs"]
        result = collection.insert_one(paragraph_data)
        return result.inserted_id

    def insert_references(self, references_data):
        collection = self.db["references"]
        result = collection.insert_many(references_data)
        return result.inserted_ids

    def get_citation_count(self, source_id):
        collection = self.db["references"]
        count = collection.count_documents({"SourceID": source_id})
        return count

    def get_sources(self):
        collection = self.db["papers"]
        sources = list(collection.find({"Source": True}))
        return sources

    def get_paper_by_doi(self, doi):
        collection = self.db["papers"]
        paper = collection.find_one({"DOI": doi})
        return paper

    def get_paper_by_title(self, title):
        collection = self.db["papers"]
        paper = collection.find_one({"Title": title})
        return paper

    def get_paragraph_by_source_id(self, source_id):
        collection = self.db["paragraphs"]
        paragraph = collection.find_one({"SourceID": source_id})
        return paragraph

    def insert__all_input_data(self, source_data, paragraph_data, citations_data):
        source_id = self.insert_paper(source_data)
        paragraph_id = self.insert_paragraph({**paragraph_data, "SourceID": source_id})
        citation_ids = self.insert_papers(citations_data)
        self.insert_references([{"SourceID": source_id, "CitationID": cit_id} for cit_id in citation_ids])
        return source_id, paragraph_id, citation_ids


    def insert_generated(self, generated_citations_data):
        collection = self.db["generated"]
        result = collection.insert_many(generated_citations_data)
        return result.inserted_ids

#db = Database()
#print(db.get_source_papers())

## Create a new client and connect to the server
#client = MongoClient(uri, server_api=ServerApi('1'))
#
## Send a ping to confirm a successful connection
#try:
#    # insert a dummy query to the test and test2 collection to confirm the connection is working
#    db = client["oaca"]
#    collection = db["test"]
#
#    print("Pinged your deployment. You successfully connected to MongoDB!")
#except Exception as e:
#    print(e)