
"""
Advanced Graph RAG Example with Neo4j Integration
This shows how to scale up to Neo4j for production use
"""

# First, install neo4j driver: pip install neo4j

from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any

class Neo4jGraphRAG:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def close(self):
        self.driver.close()
    
    def add_document(self, doc_id: str, text: str, metadata: Dict = None):
        """Add document with embedding to Neo4j"""
        embedding = self.model.encode(text).tolist()
        
        with self.driver.session() as session:
            session.write_transaction(
                self._create_document_node, 
                doc_id, text, embedding, metadata or {}
            )
    
    @staticmethod
    def _create_document_node(tx, doc_id: str, text: str, embedding: List[float], metadata: Dict):
        query = """
        CREATE (d:Document {
            id: $doc_id,
            text: $text,
            embedding: $embedding,
            metadata: $metadata
        })
        """
        tx.run(query, doc_id=doc_id, text=text, embedding=embedding, metadata=metadata)
    
    def create_entity_relationships(self, doc_id: str, entities: List[str]):
        """Create entity nodes and relationships"""
        with self.driver.session() as session:
            for entity in entities:
                session.write_transaction(
                    self._create_entity_relationship, 
                    doc_id, entity
                )
    
    @staticmethod
    def _create_entity_relationship(tx, doc_id: str, entity: str):
        query = """
        MATCH (d:Document {id: $doc_id})
        MERGE (e:Entity {name: $entity})
        MERGE (d)-[:CONTAINS]->(e)
        """
        tx.run(query, doc_id=doc_id, entity=entity)
    
    def vector_similarity_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Perform vector similarity search using Neo4j"""
        query_embedding = self.model.encode(query).tolist()
        
        with self.driver.session() as session:
            result = session.read_transaction(
                self._vector_search, 
                query_embedding, top_k
            )
            return result
    
    @staticmethod
    def _vector_search(tx, query_embedding: List[float], top_k: int):
        # Neo4j vector similarity using cosine similarity
        # Note: This is a simplified example - in practice, you'd use
        # Neo4j's vector index for better performance
        query = """
        MATCH (d:Document)
        WITH d, gds.similarity.cosine(d.embedding, $query_embedding) AS similarity
        RETURN d.id AS doc_id, d.text AS text, similarity
        ORDER BY similarity DESC
        LIMIT $top_k
        """
        result = tx.run(query, query_embedding=query_embedding, top_k=top_k)
        return [{"doc_id": record["doc_id"], 
                "text": record["text"], 
                "similarity": record["similarity"]} 
                for record in result]
    
    def graph_enhanced_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Enhanced search with graph traversal"""
        with self.driver.session() as session:
            result = session.read_transaction(
                self._graph_enhanced_search, 
                query, top_k
            )
            return result
    
    @staticmethod
    def _graph_enhanced_search(tx, query: str, top_k: int):
        # Find documents and their related documents through shared entities
        cypher_query = """
        MATCH (d:Document)
        WHERE d.text CONTAINS $query
        OPTIONAL MATCH (d)-[:CONTAINS]->(e:Entity)<-[:CONTAINS]-(related:Document)
        WHERE related <> d
        RETURN d.id AS doc_id, 
               d.text AS text,
               d.metadata AS metadata,
               collect(DISTINCT {
                   doc_id: related.id,
                   text: related.text,
                   via_entity: e.name
               }) AS related_documents
        LIMIT $top_k
        """
        result = tx.run(cypher_query, query=query, top_k=top_k)
        return [dict(record) for record in result]


# Example usage function
def demonstrate_neo4j_rag():
    """
    Demonstration of Neo4j Graph RAG
    Note: This requires a running Neo4j instance
    """
    
    # Connection details - adjust for your setup
    # For local Neo4j: neo4j://localhost:7687
    # For Aura: neo4j+s://your-instance.neo4j.io
    uri = "neo4j://localhost:7687"
    user = "neo4j"
    password = "your_password"
    
    try:
        graph_rag = Neo4jGraphRAG(uri, user, password)
        
        # Sample documents
        documents = [
            ("doc1", "High-quality wireless headphones with noise cancellation"),
            ("doc2", "Bluetooth wireless earbuds with long battery life"),
            ("doc3", "Professional studio headphones for audio editing"),
        ]
        
        # Add documents
        for doc_id, text in documents:
            graph_rag.add_document(doc_id, text)
            
            # Extract and add entities (simplified)
            entities = ["headphones", "wireless", "audio"] if "headphones" in text.lower() else []
            if entities:
                graph_rag.create_entity_relationships(doc_id, entities)
        
        # Search
        results = graph_rag.graph_enhanced_search("wireless headphones", 3)
        
        print("Neo4j Graph RAG Results:")
        for result in results:
            print(f"Document: {result['text']}")
            print(f"Related: {result['related_documents']}")
            print()
        
        graph_rag.close()
        
    except Exception as e:
        print(f"Neo4j connection error: {e}")
        print("Make sure Neo4j is running and credentials are correct")


if __name__ == "__main__":
    print("This example requires Neo4j to be installed and running")
    print("Install with: pip install neo4j")
    print("For local setup, visit: https://neo4j.com/download/")
    # demonstrate_neo4j_rag()
