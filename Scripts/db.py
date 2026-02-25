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


# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    # insert a dummy query to the test and test2 collection to confirm the connection is working
    db = client["oaca"]
    collection = db["test"]

    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)