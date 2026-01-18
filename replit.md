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
- **API Design**: RESTful JSON endpoints for user CRUD, database connection pooling, and automatic table creation.
- **Advanced RAG Implementation**: Four-stage methodology progressing from educational demos to production-ready Advanced RAG with Tavily and OpenAI integration, incorporating manufacturing intelligence and RAGAS evaluation.
- **Semantic Layer**: LangChain-based Natural Language to SQL conversion with dynamic schema introspection, safety features (SQL injection prevention, operation whitelisting), and monitoring. Includes advanced techniques like vector store retrieval (FAISS, OpenAI embeddings) and few-shot prompting with manufacturing domain examples.
- **Statistical Analysis Tools**: Two comprehensive tools for manufacturing quality control: Daily defect rate analysis and daily on-time delivery rate analysis, both with CSV upload functionality and professional reporting.
- **Excel Data Cleansing**: Web-based and CLI tool for preparing manufacturing data, supporting drag-and-drop .xlsx/.xls uploads, optional JSON schema enforcement, a 10-step automated cleansing pipeline, real-time statistics, and downloadable cleansed Excel files.
- **Document Segmentation for Hybrid RAG**: Web-based and CLI tool for segmenting Excel documents into structured blocks based on cell ranges and segment types, enabling hybrid RAG architectures.
- **Combined Cleansing + Segmentation Pipeline**: Production-ready ETL pipeline integrating data cleansing and document segmentation with multi-CSV output, schema-based column filtering, per-block cleansing, and web/terminal interfaces for processing.
- **Contextual UI Hints System**: Database-backed intelligent hint system for manufacturing terminology, acronym expansion, and query assistance, leveraging enhanced metadata and user-defined acronyms.
- **LangGraph 101 Implementation**: Entry Point series demonstrating LangGraph base class patterns for custom manufacturing tools, workflow orchestration, and agent patterns, including a Manufacturing Queue Router and Plant Log Ingestion system.
- **Structured RAG with Graph-Theoretic Determinism**: Production-ready implementation separating deterministic logic (NetworkX for join pathfinding) from LLM inference, using graph metadata stored in a relational database.
- **NetworkX Graph Patterns**: Comprehensive demonstration of network science patterns (graph construction, centrality analysis, shortest path, community detection) applied to manufacturing contexts, integrated with database schema metadata.
- **ArangoDB Graph Persistence**: Production-ready utilities for persisting NetworkX graphs to ArangoDB, supporting GPU-accelerated analytics and enabling faster session loading and team collaboration for manufacturing schema graphs.
- **Hugging Face MCP Server Integration**: Web-based interface implementing Model Context Protocol patterns for accessing Hugging Face Hub for model, dataset, and spaces search, including quick actions and authentication.
- **Manufacturing SQL Semantic Layer (HF Space)**: MCP Context Builder for GitHub Copilot with a Gradio interface allowing users to build MCP context packages, browse manufacturing schemas, view ground truth SQL, and perform interactive field disambiguation via graph traversal.
- **Schema Files**: SQLite-compatible schema for local development and original PostgreSQL schema for Replit production.

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
- **Tavily API**: For advanced RAG implementation
- **OpenAI API**: For advanced RAG implementation
- **FAISS**: For vector store retrieval in semantic layer
- **NetworkX**: Graph-theoretic algorithms
- **LangGraph**: StateGraph workflow orchestration
- **pandas**: Data manipulation and analysis
- **openpyxl**: Excel file reading and writing (.xlsx)
- **xlrd**: Legacy Excel file reading (.xls)
- **mcp**: Model Context Protocol SDK for building MCP servers and clients
- **httpx**: Modern async HTTP client for API integrations
- **sdv**: Synthetic Data Vault for realistic mock data generation (local development)
- **sdmetrics**: Metrics for evaluating synthetic data quality (local development)
- **Faker**: Realistic synthetic data generation with seed-based reproducibility (seed=42)