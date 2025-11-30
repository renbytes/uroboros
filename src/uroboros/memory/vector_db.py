import logging
import chromadb
from chromadb.api.models.Collection import Collection
from typing import List, Dict, Any, Optional

from uroboros.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class VectorDBClient:
    """
    A generic wrapper around the Vector Database.
    Currently implements ChromaDB, but designed for interchangeability.
    """

    def __init__(self, collection_name: str = "uroboros_default"):
        self.db_path = f"{settings.ROOT_DIR}/../data/chromadb"
        
        try:
            self.client = chromadb.PersistentClient(path=self.db_path)
            # Use cosine similarity (default is often L2, but cosine is better for text)
            self.collection: Collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"VectorDB initialized at {self.db_path} [{collection_name}]")
        except Exception as e:
            logger.critical(f"Failed to initialize VectorDB: {e}")
            raise

    def add_documents(
        self, 
        ids: List[str], 
        documents: List[str], 
        embeddings: List[List[float]], 
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Upserts documents into the vector store.
        """
        try:
            if not ids or not documents or not embeddings:
                logger.warning("Attempted to add empty batch to VectorDB.")
                return False

            self.collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            return True
        except Exception as e:
            logger.error(f"VectorDB Upsert Failed: {e}")
            return False

    def query(
        self, 
        query_embedding: List[float], 
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Performs a nearest-neighbor search.
        
        Args:
            query_embedding: The vector representation of the query.
            n_results: Number of matches to return.
            where: Metadata filtering (e.g., {"tags": "python"}).
            
        Returns:
            The raw ChromaDB result dictionary.
        """
        try:
            return self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )
        except Exception as e:
            logger.error(f"VectorDB Query Failed: {e}")
            return {"ids": [], "documents": [], "metadatas": [], "distances": []}

    def delete(self, ids: List[str]) -> bool:
        """Removes documents by ID."""
        try:
            self.collection.delete(ids=ids)
            return True
        except Exception as e:
            logger.error(f"VectorDB Delete Failed: {e}")
            return False

    def count(self) -> int:
        """Returns total number of documents in collection."""
        return self.collection.count()