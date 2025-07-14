
"""
NetworkX RAG Example - Graph-based Retrieval-Augmented Generation
Building on your existing vector similarity approach with graph relationships
"""

import networkx as nx
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Tuple
import json

class GraphRAG:
    def __init__(self):
        self.graph = nx.Graph()
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embeddings = {}
        
    def add_document(self, doc_id: str, text: str, metadata: Dict = None):
        """Add a document to the graph with its embedding"""
        embedding = self.model.encode(text)
        self.embeddings[doc_id] = embedding
        
        # Add document node
        self.graph.add_node(doc_id, 
                           text=text, 
                           type='document',
                           metadata=metadata or {})
        
        # Extract entities and create entity nodes
        entities = self._extract_entities(text)
        for entity in entities:
            entity_id = f"entity_{entity.lower().replace(' ', '_')}"
            if not self.graph.has_node(entity_id):
                self.graph.add_node(entity_id, 
                                   text=entity, 
                                   type='entity')
            
            # Connect document to entity
            self.graph.add_edge(doc_id, entity_id, 
                               relationship='contains')
    
    def _extract_entities(self, text: str) -> List[str]:
        """Simple entity extraction - in practice, use NER"""
        # Basic keyword extraction for demo
        keywords = []
        common_tech_terms = [
            'camera', 'digital', 'canon', 'nike', 'shoes', 'headphones',
            'wireless', 'bluetooth', 'cable', 'usb', 'iphone', 'apple'
        ]
        
        text_lower = text.lower()
        for term in common_tech_terms:
            if term in text_lower:
                keywords.append(term.title())
        
        return keywords
    
    def add_relationship(self, doc_id1: str, doc_id2: str, relationship: str):
        """Add explicit relationship between documents"""
        if self.graph.has_node(doc_id1) and self.graph.has_node(doc_id2):
            self.graph.add_edge(doc_id1, doc_id2, relationship=relationship)
    
    def vector_similarity_search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Traditional vector similarity search"""
        query_embedding = self.model.encode(query)
        
        similarities = []
        for doc_id, embedding in self.embeddings.items():
            if self.graph.nodes[doc_id]['type'] == 'document':
                similarity = np.dot(query_embedding, embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
                )
                similarities.append((doc_id, similarity))
        
        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_k]
    
    def graph_enhanced_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Enhanced search using graph relationships"""
        # Start with vector similarity
        initial_results = self.vector_similarity_search(query, top_k * 2)
        
        enhanced_results = []
        for doc_id, similarity in initial_results:
            doc_data = self.graph.nodes[doc_id]
            
            # Find related documents through graph connections
            related_docs = []
            for neighbor in self.graph.neighbors(doc_id):
                if self.graph.nodes[neighbor]['type'] == 'entity':
                    # Find other documents connected to this entity
                    for entity_neighbor in self.graph.neighbors(neighbor):
                        if (entity_neighbor != doc_id and 
                            self.graph.nodes[entity_neighbor]['type'] == 'document'):
                            related_docs.append({
                                'doc_id': entity_neighbor,
                                'connection': self.graph.nodes[neighbor]['text'],
                                'text': self.graph.nodes[entity_neighbor]['text']
                            })
            
            enhanced_results.append({
                'doc_id': doc_id,
                'text': doc_data['text'],
                'vector_similarity': similarity,
                'related_documents': related_docs[:3],  # Top 3 related
                'metadata': doc_data.get('metadata', {})
            })
        
        return enhanced_results[:top_k]
    
    def get_graph_stats(self) -> Dict:
        """Get statistics about the graph"""
        return {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'document_nodes': len([n for n in self.graph.nodes() 
                                 if self.graph.nodes[n]['type'] == 'document']),
            'entity_nodes': len([n for n in self.graph.nodes() 
                               if self.graph.nodes[n]['type'] == 'entity']),
            'connected_components': nx.number_connected_components(self.graph)
        }
    
    def visualize_connections(self, doc_id: str) -> Dict:
        """Show connections for a specific document"""
        if not self.graph.has_node(doc_id):
            return {}
        
        connections = {
            'document': self.graph.nodes[doc_id]['text'],
            'entities': [],
            'related_documents': []
        }
        
        for neighbor in self.graph.neighbors(doc_id):
            if self.graph.nodes[neighbor]['type'] == 'entity':
                connections['entities'].append(self.graph.nodes[neighbor]['text'])
                
                # Find documents connected through this entity
                for entity_neighbor in self.graph.neighbors(neighbor):
                    if (entity_neighbor != doc_id and 
                        self.graph.nodes[entity_neighbor]['type'] == 'document'):
                        connections['related_documents'].append({
                            'doc_id': entity_neighbor,
                            'text': self.graph.nodes[entity_neighbor]['text'],
                            'via_entity': self.graph.nodes[neighbor]['text']
                        })
        
        return connections


# Example usage
def main():
    # Initialize GraphRAG
    graph_rag = GraphRAG()
    
    # Add sample documents (similar to your existing data)
    documents = [
        {
            'id': 'prod_1',
            'text': 'Canon DSLR Rebel T7 Camera',
            'metadata': {'category': 'electronics', 'price': 399.99}
        },
        {
            'id': 'prod_2', 
            'text': 'Canon T7 18MP Digital Camera',
            'metadata': {'category': 'electronics', 'price': 429.99}
        },
        {
            'id': 'prod_3',
            'text': 'Red Nike Air Max shoes',
            'metadata': {'category': 'footwear', 'price': 120.00}
        },
        {
            'id': 'prod_4',
            'text': 'Nike Air Max Sneakers, Red',
            'metadata': {'category': 'footwear', 'price': 125.00}
        },
        {
            'id': 'prod_5',
            'text': 'Apple Lightning USB cable',
            'metadata': {'category': 'accessories', 'price': 19.99}
        }
    ]
    
    # Add documents to graph
    for doc in documents:
        graph_rag.add_document(doc['id'], doc['text'], doc['metadata'])
    
    # Add explicit relationships
    graph_rag.add_relationship('prod_1', 'prod_2', 'similar_product')
    graph_rag.add_relationship('prod_3', 'prod_4', 'similar_product')
    
    # Test queries
    queries = [
        "Canon digital camera",
        "Nike running shoes",
        "Apple cable"
    ]
    
    print("=== Graph-Enhanced RAG Results ===\n")
    
    for query in queries:
        print(f"Query: '{query}'")
        print("-" * 50)
        
        # Traditional vector search
        vector_results = graph_rag.vector_similarity_search(query, 3)
        print("Vector Similarity Results:")
        for doc_id, similarity in vector_results:
            text = graph_rag.graph.nodes[doc_id]['text']
            print(f"  {doc_id}: {text} (similarity: {similarity:.4f})")
        
        print("\nGraph-Enhanced Results:")
        enhanced_results = graph_rag.graph_enhanced_search(query, 3)
        for i, result in enumerate(enhanced_results, 1):
            print(f"  {i}. {result['doc_id']}: {result['text']}")
            print(f"     Similarity: {result['vector_similarity']:.4f}")
            if result['related_documents']:
                print(f"     Related via: {[r['connection'] for r in result['related_documents']]}")
        
        print("\n" + "="*60 + "\n")
    
    # Show graph statistics
    print("Graph Statistics:")
    stats = graph_rag.get_graph_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Show connections for a specific document
    print(f"\nConnections for prod_1:")
    connections = graph_rag.visualize_connections('prod_1')
    print(json.dumps(connections, indent=2))


if __name__ == "__main__":
    main()
