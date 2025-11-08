"""
Vector Store - Similarity Search for Trading Memory

Implements vector database for finding similar historical situations using RAG.
Supports both FAISS (local, fast) and ChromaDB (persistent, feature-rich).
"""

from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from loguru import logger
import pickle
from pathlib import Path
import json


class VectorStore:
    """
    Vector database for similarity search in trading history.
    
    Uses FAISS for fast similarity search with embeddings.
    Falls back to simple in-memory storage if FAISS not available.
    """
    
    def __init__(
        self,
        embedding_dim: int = 384,
        storage_path: Optional[str] = None,
        use_faiss: bool = True
    ):
        """
        Initialize vector store.
        
        Args:
            embedding_dim: Dimension of embedding vectors
            storage_path: Path to persist the vector database
            use_faiss: Whether to use FAISS (if available)
        """
        self.embedding_dim = embedding_dim
        self.storage_path = Path(storage_path) if storage_path else Path("data/vector_store")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Try to import FAISS
        self.use_faiss = use_faiss
        self.faiss_index = None
        
        if self.use_faiss:
            try:
                import faiss
                self.faiss = faiss
                # Create FAISS index (L2 distance)
                self.faiss_index = faiss.IndexFlatL2(embedding_dim)
                logger.info(f"✅ FAISS vector store initialized (dim={embedding_dim})")
            except ImportError:
                logger.warning("⚠️  FAISS not available, using simple storage")
                self.use_faiss = False
        
        # Fallback storage (always maintained)
        self.vectors: List[np.ndarray] = []
        self.metadata: List[Dict[str, Any]] = []
        
        # Load existing data if available
        self._load()
    
    def add(
        self,
        embedding: np.ndarray,
        metadata: Dict[str, Any]
    ) -> int:
        """
        Add a vector with metadata to the store.
        
        Args:
            embedding: Vector embedding (numpy array)
            metadata: Associated metadata (trade details, context, outcome)
            
        Returns:
            Index of added vector
        """
        # Ensure correct shape
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)
        
        if embedding.shape[1] != self.embedding_dim:
            raise ValueError(f"Embedding dimension mismatch: expected {self.embedding_dim}, got {embedding.shape[1]}")
        
        # Add to FAISS index if available
        if self.use_faiss and self.faiss_index is not None:
            self.faiss_index.add(embedding.astype('float32'))
        
        # Add to fallback storage
        self.vectors.append(embedding[0])
        self.metadata.append(metadata)
        
        idx = len(self.vectors) - 1
        logger.debug(f"Added vector {idx} to store")
        
        return idx
    
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for k most similar vectors.
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            
        Returns:
            List of dictionaries with 'metadata' and 'distance'
        """
        if len(self.vectors) == 0:
            return []
        
        # Ensure correct shape
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        k = min(k, len(self.vectors))  # Don't search for more than we have
        
        if self.use_faiss and self.faiss_index is not None:
            # Use FAISS for search
            distances, indices = self.faiss_index.search(
                query_embedding.astype('float32'),
                k
            )
            
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(self.metadata):  # Valid index
                    results.append({
                        'metadata': self.metadata[idx],
                        'distance': float(dist),
                        'similarity': 1.0 / (1.0 + float(dist))  # Convert to similarity score
                    })
        else:
            # Fallback: compute distances manually
            vectors_array = np.array(self.vectors)
            distances = np.linalg.norm(vectors_array - query_embedding, axis=1)
            
            # Get top k indices
            top_k_indices = np.argsort(distances)[:k]
            
            results = []
            for idx in top_k_indices:
                results.append({
                    'metadata': self.metadata[idx],
                    'distance': float(distances[idx]),
                    'similarity': 1.0 / (1.0 + float(distances[idx]))
                })
        
        logger.debug(f"Found {len(results)} similar vectors")
        return results
    
    def save(self) -> None:
        """Save vector store to disk."""
        try:
            # Save metadata and vectors
            data = {
                'vectors': self.vectors,
                'metadata': self.metadata,
                'embedding_dim': self.embedding_dim
            }
            
            with open(self.storage_path / 'store.pkl', 'wb') as f:
                pickle.dump(data, f)
            
            # Save FAISS index if available
            if self.use_faiss and self.faiss_index is not None:
                self.faiss.write_index(
                    self.faiss_index,
                    str(self.storage_path / 'faiss.index')
                )
            
            logger.info(f"💾 Vector store saved to {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")
    
    def _load(self) -> None:
        """Load vector store from disk."""
        try:
            store_file = self.storage_path / 'store.pkl'
            if not store_file.exists():
                logger.info("No existing vector store found, starting fresh")
                return
            
            with open(store_file, 'rb') as f:
                data = pickle.load(f)
            
            self.vectors = data.get('vectors', [])
            self.metadata = data.get('metadata', [])
            
            # Load FAISS index if available
            if self.use_faiss:
                faiss_file = self.storage_path / 'faiss.index'
                if faiss_file.exists():
                    self.faiss_index = self.faiss.read_index(str(faiss_file))
            
            logger.info(f"📂 Loaded vector store with {len(self.vectors)} vectors")
        except Exception as e:
            logger.warning(f"Could not load vector store: {e}, starting fresh")
    
    def clear(self) -> None:
        """Clear all data from the vector store."""
        self.vectors = []
        self.metadata = []
        
        if self.use_faiss and self.faiss_index is not None:
            self.faiss_index = self.faiss.IndexFlatL2(self.embedding_dim)
        
        logger.info("🧹 Vector store cleared")
    
    def __len__(self) -> int:
        """Return number of vectors in the store."""
        return len(self.vectors)
    
    def __repr__(self) -> str:
        """String representation."""
        backend = "FAISS" if self.use_faiss else "Simple"
        return f"VectorStore(backend={backend}, size={len(self)}, dim={self.embedding_dim})"
