import logging
import json
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Optional
from openai import AsyncOpenAI

from uroboros.core.interfaces import MemoryInterface
from uroboros.core.types import Skill
from uroboros.core.config import get_settings
from uroboros.core.utils import timer

logger = logging.getLogger(__name__)
settings = get_settings()

class VoyagerMemory(MemoryInterface):
    """
    Implementation of the Skill Library using ChromaDB.
    Stores and retrieves coding skills based on semantic similarity.
    """

    def __init__(self):
        self.collection_name = "uroboros_skills"
        
        # Initialize OpenAI for Embeddings
        self.embedding_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY.get_secret_value()
        )
        
        # Initialize ChromaDB (Persistent)
        # We store the DB in the project root under /data
        db_path = f"{settings.ROOT_DIR}/../data/chromadb"
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        
        # Get or Create Collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"} # Use Cosine Similarity
        )

    async def _get_embedding(self, text: str) -> List[float]:
        """
        Generates a vector embedding for the given text using OpenAI.
        """
        try:
            response = await self.embedding_client.embeddings.create(
                input=text.replace("\n", " "), # Normalize newlines
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def retrieve_relevant_skills(self, query: str, limit: int = 3) -> List[Skill]:
        """
        RAG: Finds the most relevant code snippets for the current task.
        """
        with timer(logger, "Skill Retrieval"):
            query_vector = await self._get_embedding(query)

            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=limit
            )

            skills: List[Skill] = []
            
            # Check if we got results (Chroma returns nested lists)
            if not results["ids"] or not results["ids"][0]:
                logger.info("No relevant skills found in memory.")
                return []

            # Unpack Chroma results
            ids = results["ids"][0]
            metadatas = results["metadatas"][0]
            documents = results["documents"][0] # The code content

            for i in range(len(ids)):
                meta = metadatas[i]
                code = documents[i]
                
                # Reconstruct Skill object
                skill = Skill(
                    name=meta.get("name", "unknown"),
                    docstring=meta.get("docstring", ""),
                    code=code,
                    tags=json.loads(meta.get("tags", "[]"))
                )
                skills.append(skill)
            
            logger.info(f"Retrieved {len(skills)} skills for query: '{query[:50]}...'")
            return skills

    async def store_skill(self, skill: Skill) -> None:
        """
        Indexes a new verified skill.
        Example: The Actor creates a new tool 'parse_csv.py'. We store it here.
        """
        logger.info(f"Learning new skill: {skill.name}")

        # Create a rich semantic representation for the embedding
        # We combine the docstring and the code to capture both intent and implementation
        text_to_embed = f"{skill.docstring}\n\n{skill.code}"
        embedding = await self._get_embedding(text_to_embed)

        self.collection.upsert(
            ids=[skill.name], # Use function name as ID (assumes uniqueness)
            embeddings=[embedding],
            documents=[skill.code],
            metadatas=[{
                "name": skill.name,
                "docstring": skill.docstring,
                "tags": json.dumps(skill.tags),
                "timestamp": str(settings.ENVIRONMENT)
            }]
        )