from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from keys import DB_KEY

uri = DB_KEY

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