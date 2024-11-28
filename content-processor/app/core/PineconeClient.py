import os

from dotenv import load_dotenv
from pinecone import Pinecone

if (os.path.exists('.env')):
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

    def create_index(self):
        try:
            self.client.create_index(
                index_name=self.index_name, dimension=1024, metric="cosine")
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

    def query(self, query_vector, top_k):
        try:
            index = self.get_index()
            return index.query(query_vector=query_vector, top_k=top_k, include_values=True, include_metadata=True)
        except Exception as e:
            print(f"Error querying index: {e}")
            return None

    def upsert(self, data, batch_size=100):
        try:
            index = self.get_index()
            valid_data = []
            for item in data:
                if not isinstance(item, dict):
                    print(f"Warning: Invalid item type: {type(item)}")
                    continue
                if 'id' not in item or 'values' not in item:
                    print(f"Warning: Missing 'id' or 'values' in item: {item}")
                    continue
                if item['values'] is None:
                    print(
                        f"Warning: 'values' is None for item with ID {item['id']}")
                    continue
                valid_data.append(item)

            if not valid_data:
                print("No valid data to upsert")
                return None
            return index.upsert(vectors=valid_data, batch_size=batch_size)
        except Exception as e:
            print(f"Error upserting data: {e}")
            # print(f"Data causing error: {data[0]}")
            return None

    def upsert_batch(self, vectors, batch_size=100):
        print(
            f"Upserting {len(vectors)} vectors in batches of {batch_size}...")
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            # Filter out any invalid vectors
            valid_batch = [v for v in batch if isinstance(
                v, dict) and 'id' in v and 'values' in v and v['values'] is not None]
            if len(valid_batch) != len(batch):
                print(
                    f"Warning: Filtered out {len(batch) - len(valid_batch)} invalid vectors from batch {i//batch_size + 1}")
            try:
                if valid_batch:
                    upsert_response = self.upsert(valid_batch)
                    # print(ss
                    # f'Upserted batch {i//batch_size + 1}: {upsert_response}')
                else:
                    print(
                        f"Skipping batch {i//batch_size + 1} as it contains no valid vectors")
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
