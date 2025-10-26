# Python Educational Script with Flask Application

## Overview

This project provides an interactive Python educational script for learning basic programming concepts, complemented by a Flask web application and an Astro demonstration. Its core purpose is to facilitate learning through practical examples and hands-on exercises, with a focus on building business intelligence applications for the manufacturing industry. Key capabilities include a RESTful API with user management, advanced RAG-assisted SQL generation, statistical analysis tools for quality control, and a modern frontend framework integration. The project aims to prepare users for working with APIs in an aerospace manufacturing context, integrating AI strategies, and demonstrating production-ready application development.

## User Preferences

Preferred communication style: Simple, everyday language.
Technical preferences: LangChain for semantic layer, comprehensive safety guardrails for SQL execution, production-ready architecture with monitoring.
JavaScript framework interest: Exploring Astro as modern frontend framework to complement Flask backend, interested in Teachable Machine analogy for understanding framework concepts.
Learning path: Advanced Python for business applications, preparing to work with APIs at aerospace manufacturing company, enrolled in AI learning for Business leaders (Berkeley Haas), needs CSV upload and processing capabilities for work projects.
Capstone project: Creating semantic layer using LangChain for Berkeley Haas AI strategy class, focusing on business intelligence and natural language to SQL conversion for manufacturing industry applications.
Development approach: Learning-first methodology - prefers understanding building blocks thoroughly before integration to avoid unnecessary API costs. Systematic 123[n..]_Entry_Point_Topic.py naming convention for incremental Frank Kane Advanced RAG study.
API management: Cost-conscious development with OpenAI quota awareness, confirmed pay-as-you-go Tavily integration, prefers demo modes for initial learning before live API usage.
LangGraph 101 Discovery: Successfully identified and implemented the foundational LangGraph base class patterns from langchain-ai/agents-from-scratch/langgraph_101.ipynb, enabling direct adaptation of email assistant pattern to manufacturing intelligence with proper StateGraph, tool calling loops, and workflow orchestration.

## System Architecture

### Backend
- **Framework**: Flask (Python web framework)
- **ORM**: SQLAlchemy with Flask-SQLAlchemy
- **Database**: PostgreSQL
- **API Design**: RESTful JSON endpoints
- **Core Features**: User CRUD operations, database connection pooling, automatic table creation.
- **Advanced RAG Implementation**: Four-stage methodology progressing from educational demos to production-ready Advanced RAG with Tavily and OpenAI integration, incorporating manufacturing intelligence and RAGAS evaluation.
- **Semantic Layer**: LangChain-based NL to SQL conversion with dynamic schema introspection, safety features (SQL injection prevention, operation whitelisting), and monitoring. Includes advanced techniques like vector store retrieval (FAISS, OpenAI embeddings) and few-shot prompting with manufacturing domain examples.
- **Statistical Analysis Tools**: Two comprehensive tools for manufacturing quality control:
    - Daily defect rate analysis (Z-tests, confidence intervals)
    - Daily on-time delivery rate analysis (Z-tests, confidence intervals)
    Both include CSV upload functionality and professional reporting.
- **Contextual UI Hints System**: Intelligent hint system for manufacturing terminology, acronym expansion, and query assistance, exposed via `/api/hints` and `/api/acronym/<acronym>` endpoints.
- **LangGraph 101 Implementation**: Complete Entry Point series (010-017) demonstrating LangGraph base class patterns:
    - Custom manufacturing tools registry system
    - StateGraph workflow orchestration
    - Tool calling loop agent patterns
    - Direct email→manufacturing assistant adaptation following langchain-ai/agents-from-scratch architecture
    - Manufacturing Queue Router system with proper edges/nodes configuration (inbox→queue adaptation)
    - Manufacturing Plant Log Ingestion system adapted from Gmail ingestion for plant operations data processing
- **Structured RAG with Graph-Theoretic Determinism (Entry Point 018)**: Production-ready implementation separating concerns between deterministic logic and LLM inference:
    - Graph metadata storage in relational database (schema_nodes, schema_edges tables)
    - NetworkX integration for deterministic join pathfinding via shortest path algorithms
    - Three-phase RAG workflow: retrieval (NetworkX), augmentation (structural context), grounded generation (LLM)
    - Hybrid retrieval strategy: RAG over unstructured data (ChromaDB/FAISS semantic similarity) + RAG over structured data (graph-embedded schema relationships)
    - Principle of logical determinism: Graph theory guarantees correct multi-hop join sequences, offloading structural navigation from LLM inference to reliable algorithms
    - Directionally consistent join metadata ensures accurate SQL generation context for manufacturing intelligence queries
- **NetworkX Graph Patterns (Entry Point 019)**: Comprehensive demonstration of network science patterns from Edward L. Platt's "Network Science with Python and NetworkX Quick Start Guide" (Packt, 2019):
    - Graph construction patterns: simple (undirected), directed (DAG), weighted, and database-loaded graphs
    - Centrality analysis: degree, betweenness, closeness centrality measures for identifying critical nodes
    - Shortest path algorithms applied to manufacturing contexts (supply chains, process flows)
    - Community detection for identifying equipment clusters and process groups
    - Graph-level metrics: density, connectivity, clustering coefficients
    - Integration with Entry Point 018 database schema metadata for practical manufacturing intelligence applications
- **ArangoDB Graph Persistence (Entry Point 020)**: Production-ready graph persistence utilities based on NVIDIA Developer Blog "Accelerated, Production-Ready Graph Analytics for NetworkX Users":
    - nx-arangodb integration for persisting NetworkX graphs to ArangoDB database
    - Utility classes for ArangoDB configuration and connection management
    - Graph persistence patterns: create locally → persist to ArangoDB → load in new sessions → collaborate with team
    - Integration with Entry Points 018 (schema graphs) and 019 (manufacturing networks) for production deployment
    - Supports GPU-accelerated analytics with nx-cugraph backend (11-600x speedup for betweenness centrality)
    - 3x faster session loading when graphs persisted in ArangoDB vs. loading from source
    - Environment variable-based credential management for security best practices
    - **Second Pass (020_Entry_Point_Persist_2nd_NetworkX_Arango.py)**: Advanced production patterns:
        - Node metadata preservation (labels, types, attributes) for identification after loading
        - Label-to-ID mapping pattern for intuitive node access post-persistence
        - Advanced NetworkX algorithms (centrality analysis, shortest paths) on ArangoDB-backed graphs
        - Schema graph integration with Entry Point 018 (supply_chain_2025_q1 graph loading)
        - Team collaboration workflow demonstrating single source of truth pattern
        - Full NetworkX API compatibility with ArangoDB backend storage

### Frontend
- **Framework**: Astro with React integration
- **Features**: File-based routing, component architecture, interactive Teachable Machine simulation, and live Flask API connection testing.
- **UI/UX**: Professional gradient design with hover effects, smooth transitions, and interactive elements for contextual hints.

## External Dependencies

- **Flask**: Web framework
- **Flask-SQLAlchemy**: ORM integration for Flask
- **SQLAlchemy**: Object-relational mapping
- **psycopg2-binary**: PostgreSQL adapter
- **LangChain**: Framework for developing applications powered by language models (for semantic layer)
- **requests**: HTTP client
- **beautifulsoup4**: HTML parsing
- **lxml**: XML/HTML parsing
- **trafilatura**: Web content extraction
- **Tavily API**: For advanced RAG implementation (real-time manufacturing intelligence)
- **OpenAI API**: For advanced RAG implementation (embeddings, LLM judge)
- **FAISS**: For vector store retrieval in semantic layer
- **NetworkX**: Graph-theoretic algorithms for deterministic join pathfinding in Structured RAG implementation
- **LangGraph**: StateGraph workflow orchestration and agent patterns (installed for LangGraph 101 Entry Points)