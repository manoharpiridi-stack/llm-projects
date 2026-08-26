from __future__ import annotations

import chromadb
from sentence_transformers import SentenceTransformer

from car_hunter.config import CHROMA_PATH, COLLECTION_NAME, EMBEDDING_MODEL
from car_hunter.listings import CarListing


class CarIndex:
    def __init__(self):
        self.encoder = SentenceTransformer(EMBEDDING_MODEL)
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        self.collection = self.client.get_or_create_collection(COLLECTION_NAME)

    def build(self, listings: list[CarListing], batch_size: int = 256) -> None:
        if self.collection.count() > 0:
            self.client.delete_collection(COLLECTION_NAME)
            self.collection = self.client.get_or_create_collection(COLLECTION_NAME)

        for start in range(0, len(listings), batch_size):
            chunk = listings[start : start + batch_size]
            docs = [item.description for item in chunk]
            embeddings = self.encoder.encode(docs).astype(float).tolist()
            self.collection.add(
                ids=[str(start + i) for i in range(len(chunk))],
                documents=docs,
                embeddings=embeddings,
                metadatas=[
                    {"price": item.price, "title": item.title, "manufacturer": item.manufacturer}
                    for item in chunk
                ],
            )

    def query(self, description: str, n_results: int = 5) -> tuple[list[str], list[float]]:
        vector = self.encoder.encode([description]).astype(float).tolist()
        result = self.collection.query(query_embeddings=vector, n_results=n_results)
        docs = result["documents"][0] if result["documents"] else []
        prices = [float(meta["price"]) for meta in (result["metadatas"][0] or [])]
        return docs, prices
