"""
Hybrid retrieval with Qdrant (BM25 + Semantic).

Combines keyword-based (BM25) and semantic (embedding) search for optimal
construction standards retrieval.
"""
import logging
import os
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
from langchain_openai import OpenAIEmbeddings
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Hybrid retriever combining BM25 (keyword) and semantic (embedding) search.
    
    BM25 excels at exact symbol matching (e.g., "MH" = manhole).
    Semantic search captures contextual meaning.
    Results are fused using reciprocal rank fusion.
    """
    
    def __init__(
        self,
        qdrant_url: str = None,
        collection_name: str = "construction_standards",
        use_memory: bool = None
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            qdrant_url: Qdrant server URL (defaults to env var or localhost)
            collection_name: Name of Qdrant collection
            use_memory: Use in-memory Qdrant (True) or server (False). Auto-detects if None.
        """
        self.collection_name = collection_name
        
        # Auto-detect: try server first, fallback to memory
        if use_memory is None:
            try:
                test_client = QdrantClient(url="http://localhost:6333", timeout=2)
                test_client.get_collections()
                use_memory = False
                logger.info("Qdrant server detected, using server mode")
            except Exception:
                use_memory = True
                logger.info("Qdrant server not available, using in-memory mode")
        
        self.use_memory = use_memory
        
        # Initialize Qdrant client
        if use_memory:
            self.client = QdrantClient(":memory:")
            logger.info("Connected to Qdrant (in-memory mode)")
        else:
            self.qdrant_url = qdrant_url or os.getenv(
                "QDRANT_URL",
                "http://localhost:6333"
            )
            self.client = QdrantClient(url=self.qdrant_url)
            logger.info(f"Connected to Qdrant at {self.qdrant_url}")
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small"
        )
        
        # BM25 index (in-memory)
        self.bm25: BM25Okapi = None
        self.documents: List[Dict[str, Any]] = []
        self.doc_ids: List[int] = []
        
        # Try to load existing collection and build BM25
        self._init_bm25_from_collection()
        
        logger.info("Hybrid retriever initialized")
    
    def _init_bm25_from_collection(self):
        """Initialize BM25 index from existing Qdrant collection."""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_exists = any(
                c.name == self.collection_name
                for c in collections.collections
            )
            
            if not collection_exists:
                logger.info("Collection doesn't exist yet, BM25 will be built on creation")
                return
            
            # Scroll through all points to get documents
            offset = None
            all_points = []
            
            while True:
                batch = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                
                points, offset = batch
                all_points.extend(points)
                
                if offset is None:
                    break
            
            if not all_points:
                logger.warning("Collection is empty, BM25 not built")
                return
            
            # Extract documents
            texts = []
            for point in all_points:
                content = point.payload.get("content", "")
                texts.append(content)
                self.documents.append({
                    "id": point.id,
                    "content": content,
                    "metadata": {
                        "discipline": point.payload.get("discipline"),
                        "category": point.payload.get("category"),
                        "source": point.payload.get("source"),
                        "reference": point.payload.get("reference", "")
                    }
                })
                self.doc_ids.append(point.id)
            
            # Build BM25 index
            tokenized_corpus = [doc.lower().split() for doc in texts]
            self.bm25 = BM25Okapi(tokenized_corpus)
            
            logger.info(f"✅ BM25 index built from collection ({len(texts)} documents)")
        
        except Exception as e:
            logger.warning(f"Could not initialize BM25 from collection: {e}")
    
    def create_collection(
        self,
        standards: List[Dict[str, Any]],
        embedding_size: int = 1536
    ):
        """
        Create Qdrant collection and index standards.
        
        Args:
            standards: List of standard dicts with 'id', 'content', 'metadata'
            embedding_size: Size of embedding vectors (1536 for text-embedding-3-small)
        """
        logger.info(f"Creating collection '{self.collection_name}'...")
        
        # Delete collection if exists
        try:
            self.client.delete_collection(self.collection_name)
            logger.info("Deleted existing collection")
        except Exception:
            pass
        
        # Create collection
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=embedding_size,
                distance=Distance.COSINE
            )
        )
        logger.info(f"Created collection with {embedding_size}-dim vectors")
        
        # Prepare documents
        texts = [s["content"] for s in standards]
        metadatas = [s["metadata"] for s in standards]
        ids = [s["id"] for s in standards]
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} standards...")
        embeddings = self.embeddings.embed_documents(texts)
        logger.info("Embeddings generated")
        
        # Upload to Qdrant
        points = []
        for i, (doc_id, embedding, text, metadata) in enumerate(
            zip(ids, embeddings, texts, metadatas)
        ):
            point = PointStruct(
                id=doc_id,
                vector=embedding,
                payload={
                    "content": text,
                    "discipline": metadata.get("discipline"),
                    "category": metadata.get("category"),
                    "source": metadata.get("source"),
                    "reference": metadata.get("reference", "")
                }
            )
            points.append(point)
        
        # Batch upload
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        logger.info(f"Uploaded {len(points)} points to Qdrant")
        
        # Build BM25 index
        logger.info("Building BM25 index...")
        tokenized_corpus = [doc.lower().split() for doc in texts]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.documents = [
            {"id": doc_id, "content": text, "metadata": meta}
            for doc_id, text, meta in zip(ids, texts, metadatas)
        ]
        self.doc_ids = ids
        logger.info("BM25 index built")
        
        logger.info("✅ Collection creation complete!")
    
    def retrieve_semantic(
        self,
        query: str,
        k: int = 5,
        discipline: str = None,
        category: str = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic retrieval using embeddings.
        
        Args:
            query: Search query
            k: Number of results to return
            discipline: Optional discipline filter (storm, sanitary, water, general)
            category: Optional category filter (cover_depth, material, etc.)
        
        Returns:
            List of dicts with 'content', 'metadata', 'score'
        """
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        
        # Build filter
        must_conditions = []
        if discipline:
            must_conditions.append(
                FieldCondition(
                    key="discipline",
                    match=MatchValue(value=discipline)
                )
            )
        if category:
            must_conditions.append(
                FieldCondition(
                    key="category",
                    match=MatchValue(value=category)
                )
            )
        
        query_filter = Filter(must=must_conditions) if must_conditions else None
        
        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=k,
            query_filter=query_filter
        )
        
        # Format results
        formatted = []
        for hit in results:
            formatted.append({
                "id": hit.id,
                "content": hit.payload["content"],
                "metadata": {
                    "discipline": hit.payload.get("discipline"),
                    "category": hit.payload.get("category"),
                    "source": hit.payload.get("source"),
                    "reference": hit.payload.get("reference", "")
                },
                "score": hit.score,
                "retrieval_method": "semantic"
            })
        
        logger.info(f"Semantic search: {len(formatted)} results for '{query}'")
        return formatted
    
    def retrieve_bm25(
        self,
        query: str,
        k: int = 5,
        discipline: str = None,
        category: str = None
    ) -> List[Dict[str, Any]]:
        """
        BM25 keyword retrieval.
        
        Args:
            query: Search query
            k: Number of results to return
            discipline: Optional discipline filter
            category: Optional category filter
        
        Returns:
            List of dicts with 'content', 'metadata', 'score'
        """
        if self.bm25 is None:
            logger.warning("BM25 index not built yet")
            return []
        
        # Tokenize query
        tokenized_query = query.lower().split()
        
        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top k indices
        top_indices = scores.argsort()[-k:][::-1]
        
        # Format results with filtering
        formatted = []
        for idx in top_indices:
            doc = self.documents[idx]
            
            # Apply filters
            if discipline and doc["metadata"].get("discipline") != discipline:
                if doc["metadata"].get("discipline") != "general":
                    continue
            if category and doc["metadata"].get("category") != category:
                continue
            
            formatted.append({
                "id": doc["id"],
                "content": doc["content"],
                "metadata": doc["metadata"],
                "score": float(scores[idx]),
                "retrieval_method": "bm25"
            })
        
        logger.info(f"BM25 search: {len(formatted)} results for '{query}'")
        return formatted[:k]
    
    def retrieve_hybrid(
        self,
        query: str,
        k: int = 5,
        discipline: str = None,
        category: str = None,
        alpha: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval with reciprocal rank fusion.
        
        Args:
            query: Search query
            k: Number of results to return
            discipline: Optional discipline filter
            category: Optional category filter
            alpha: Weight for semantic vs BM25 (0.5 = equal weight)
        
        Returns:
            Fused and ranked results
        """
        # Retrieve from both methods
        semantic_results = self.retrieve_semantic(
            query, k=k*2, discipline=discipline, category=category
        )
        bm25_results = self.retrieve_bm25(
            query, k=k*2, discipline=discipline, category=category
        )
        
        # Reciprocal rank fusion
        fused = self._reciprocal_rank_fusion(
            [semantic_results, bm25_results],
            k=k
        )
        
        logger.info(f"Hybrid search: {len(fused)} fused results for '{query}'")
        return fused
    
    def _reciprocal_rank_fusion(
        self,
        result_lists: List[List[Dict]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Fuse multiple result lists using reciprocal rank fusion.
        
        RRF score = sum(1 / (k + rank)) for each list
        
        Args:
            result_lists: List of result lists from different retrievers
            k: Constant for RRF (typically 60)
        
        Returns:
            Fused and sorted results
        """
        # Collect all unique documents
        doc_scores = {}
        
        for results in result_lists:
            for rank, doc in enumerate(results, start=1):
                doc_id = doc["id"]
                rrf_score = 1.0 / (k + rank)
                
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        "doc": doc,
                        "score": 0.0,
                        "sources": []
                    }
                
                doc_scores[doc_id]["score"] += rrf_score
                doc_scores[doc_id]["sources"].append(doc["retrieval_method"])
        
        # Sort by fused score
        sorted_docs = sorted(
            doc_scores.values(),
            key=lambda x: x["score"],
            reverse=True
        )
        
        # Format output
        fused_results = []
        for item in sorted_docs[:k]:
            doc = item["doc"].copy()
            doc["fused_score"] = item["score"]
            doc["retrieval_methods"] = list(set(item["sources"]))
            fused_results.append(doc)
        
        return fused_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "bm25_documents": len(self.documents) if self.bm25 else 0
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}

