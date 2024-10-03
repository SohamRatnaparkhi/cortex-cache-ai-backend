import os

from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()


class PineconeClient:
    def __init__(self):
        self.api_key = os.getenv("PINECONE_API_KEY")
        # self.index_name = "jina-embeddings-v2-base-en"
        self.index_name = "jina-embeddings-v3"
        self.index = None
        self.client = self.connect()

    def connect(self):
        try:
            return Pinecone(api_key=self.api_key)
        except Exception as e:
            print(f"Error connecting to Pinecone: {e}")
            return None

    def create_index(self, index_name):
        try:
            self.client.create_index(
                index_name=index_name, dimension=768, metric="cosine")
            return self.client
        except Exception as e:
            print(f"Error creating index: {e}")
            return None

    def describe_index(self):
        return self.client.describe_index(index_name=self.index_name)

    def delete_index(self):
        self.client.delete_index(index_name=self.index_name)
        self.index_name = None
        return self.client

    def get_index(self):
        if self.index is None:
            self.index = self.client.Index(name=self.index_name)
        return self.index

    def list_indexes(self):
        return self.client.list_indexes()

    def query(self, vector, top_k, filters: dict):
        try:
            index = self.get_index()
            return index.query(vector=vector, top_k=top_k, include_values=False, include_metadata=True, filter=filters)
        except Exception as e:
            print(f"Error querying index: {e}")
            return None

    def upsert(self, data):
        try:
            index = self.get_index()
            print(self.index_name)
            print(self.api_key)
            print('-------')
            print(index)
            return index.upsert(vectors=data)
        except Exception as e:
            print(f"Error upserting data: {e}")
            return None

    def upsert_batch(self, vectors, batch_size=100):
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            try:
                upsert_response = self.upsert(batch)
                print(f'Upserted batch {i//batch_size + 1}: {upsert_response}')
            except Exception as upsert_error:
                print(
                    f"Error upserting batch {i//batch_size + 1}: {str(upsert_error)}")

    def delete(self, ids):
        try:
            index = self.get_index()
            return index.delete(ids=ids)
        except Exception as e:
            print(f"Error deleting data: {e}")
            return None

    def update(self, data, id, metadata):
        try:
            index = self.get_index()
            return index.update(id=id, values=data, set_metadata=metadata)
        except Exception as e:
            print(f"Error updating data: {e}")
            return None

    def describe_index_stats(self):
        index = self.get_index()
        return index.describe_index_stats()

    def fetch(self, ids):
        index = self.get_index()
        return index.fetch(ids=ids)
