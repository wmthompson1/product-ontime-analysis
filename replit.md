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
- **Excel Data Cleansing**: Web-based and CLI tool (`/excel-cleansing`, `021_Entry_Point_Excel_Data_Cleansing.py`) for preparing manufacturing data, supporting drag-and-drop .xlsx/.xls uploads, optional JSON schema enforcement, a 10-step automated cleansing pipeline (NBSP removal, missing value imputation, duplicate removal, outlier detection), real-time statistics, and downloadable cleansed Excel files.
- **Document Segmentation for Hybrid RAG**: Web-based and CLI tool (`/document-segmentation`, `022_Entry_Point_Document_Segmentation.py`) for segmenting Excel documents into structured blocks based on cell ranges and segment types (Free-form for metadata, Tabular-form for structured data), enabling hybrid RAG architectures.
- **Combined Cleansing + Segmentation Pipeline**: Production-ready ETL pipeline (`/combined-pipeline`, `023_Entry_Point_Combined_Pipeline.py`, `app/combined_pipeline.py`) integrating data cleansing and document segmentation with multi-CSV output:
    - **Core Architecture**: Refactored `cleanse_dataframe(df, schema_dict)` in `app/excel_cleansing.py` provides reusable DataFrame cleansing shared across web upload and combined pipeline workflows
    - **Segmentation Scheme Format** (CSV): `Doc,block,upper_left,lower_right,Segment type,Block_output_csv,schema_number`
        - Schema numbering: 0 = no enforcement (default, keeps all columns), 1+ = specific schema enforcement
        - Default behavior: Both blocks use schema 0 (no filtering)
        - Example with schemas: Block 1 uses schema 1 (`schema_1.json`), Block 2 uses schema 2 (`schema_2.json`)
        - Schemas use raw Excel column names (match what you see in Excel: spaces, "#", etc.), output is automatically normalized
        - Free-form blocks are transposed: key-value pairs → single-row DataFrame with columns per metadata field
        - Tabular blocks remain tabular: header row + data rows → DataFrame
    - **Schema-Based Column Filtering**: Automatically filters DataFrame columns to keep only those defined in the schema, with comprehensive statistics tracking:
        - `columns_filtered`: count of columns dropped
        - `columns_dropped`: list of dropped column names
        - `columns_missing`: list of schema columns not found in data
        - Validation warnings for schema/data mismatches
        - Warning merge logic preserves telemetry from both filtering and cleansing stages
    - **Per-Block Cleansing**: Each segmented block is independently cleansed with NBSP removal, missing value imputation, duplicate removal, text standardization, outlier detection, and optional schema enforcement
    - **Multi-CSV Output**: Outputs separate CSV files per block (e.g., `identity.csv` for invoice metadata, `Data.csv` for delivery performance table)
    - **Web Interface** (`/combined-pipeline`): Drag-and-drop Excel upload with optional segmentation scheme CSV and schema JSON, ZIP download of all generated CSVs
    - **Terminal Interface**: `python 023_Entry_Point_Combined_Pipeline.py invoice.xlsx --scheme scheme.csv --schema schema.json --preview`
    - **Real-world Test Results**: 
        - **Default (no schemas)**: Invoice sample outputs `identity.csv` (3 columns) and `Data.csv` (5 columns including col_3, col_4)
        - **With schemas**: Same invoice with schema_1 and schema_2 filters to `identity.csv` (3 columns) and `Data.csv` (3 columns, col_3/col_4 dropped)
    - **Production ETL Use Case**: Perfect for invoice processing workflows requiring separate metadata and tabular data outputs for downstream systems, with automatic column filtering for data quality control
    - **Architect Reviewed**: Pass - cleanly reuses `cleanse_dataframe` across entry points, correct free-form transpose logic, comprehensive statistics tracking with proper warning merge, production-ready for stated ETL use case
- **Contextual UI Hints System**: Database-backed intelligent hint system (`app/database_hints_loader.py`) for manufacturing terminology, acronym expansion, and query assistance, leveraging enhanced metadata from `schema_edges` table, table-aware hints, and user-defined acronyms.
- **LangGraph 101 Implementation**: Entry Point series (010-017) demonstrating LangGraph base class patterns for custom manufacturing tools, workflow orchestration, and agent patterns, including a Manufacturing Queue Router and Plant Log Ingestion system.
- **Structured RAG with Graph-Theoretic Determinism**: Production-ready implementation (Entry Point 018) separating deterministic logic (NetworkX for join pathfinding via shortest path algorithms) from LLM inference, using graph metadata stored in a relational database (`schema_nodes`, `schema_edges`).
- **NetworkX Graph Patterns**: Comprehensive demonstration (Entry Point 019) of network science patterns (graph construction, centrality analysis, shortest path, community detection) applied to manufacturing contexts, integrated with database schema metadata.
- **ArangoDB Graph Persistence**: Production-ready utilities (Entry Point 020) for persisting NetworkX graphs to ArangoDB, supporting GPU-accelerated analytics and enabling faster session loading and team collaboration for manufacturing schema graphs.
- **Hugging Face MCP Server Integration**: Web-based interface (`/huggingface-mcp`, `app/huggingface_mcp.py`) implementing Model Context Protocol patterns for accessing Hugging Face Hub:
    - **Model Search**: Find ML models including text-to-SQL models for manufacturing semantic layer (SQLCoder, T5, etc.)
    - **Dataset Search**: Discover manufacturing and quality control datasets for training and evaluation
    - **Spaces Search**: Explore ML-powered applications and demos
    - **Quick Actions**: Pre-configured searches for text-to-SQL, manufacturing, SQLCoder, and tabular data models
    - **MCP Tools**: Exposes structured tool definitions following Model Context Protocol conventions
    - **Authentication**: Uses HUGGINGFACE_TOKEN secret for API access
- **Manufacturing SQL Semantic Layer (HF Space)**: MCP Context Builder for GitHub Copilot (`hf-space-inventory-sqlgen/`) on port 5000:
    - **MCP Context Builder**: Single "Copy to Copilot" button bundles Prompts + Resources + Tools + Semantic Context
    - **Gradio Interface** (5 tabs): Copilot Context, Schema, Ground Truth SQL, Semantic Graph, MCP Endpoints
    - **Copilot Context Tab**: Build MCP context package with question prompt, schema DDL (top 10 tables), ground truth SQL examples, and semantic layer metadata (intent, perspective, elevated concepts)
    - **Schema Tab**: Browse SQLite DDL for manufacturing tables
    - **Ground Truth SQL Tab**: View validated queries by category (quality_control, supplier_performance, equipment_reliability, production_analytics)
    - **Semantic Graph Tab**: Interactive field disambiguation via graph traversal - select intent and ambiguous field to resolve correct concept/table through `(:Intent) -[:OPERATES_WITHIN]-> (:Perspective) -[:USES_DEFINITION]-> (:Concept) <-[:CAN_MEAN]- (:Field)` path
    - **MCP Endpoints Tab**: API documentation for AI agent integration
    - **Semantic Graph Implementation** (per uploaded treatise):
        - `schema_concepts` (19 manufacturing concepts): defect_rate, quality_score, lead_time, throughput, inventory_levels, etc.
        - `schema_perspectives` (5 organizational views): Quality, Operations, Finance, Customer, Supplier
        - `schema_intents` (11 analytical intents): SupplierEvaluation, QualityTrending, ProductionOptimization, etc.
        - `schema_intent_perspectives`: OPERATES_WITHIN relationship (binary elevation: 1.0 = elevated, 0.0 = suppressed)
        - `schema_concept_fields`: CAN_MEAN relationship linking concepts to physical table.column
        - `schema_intent_concepts`: Concept elevation per intent (binary factor weights)
        - `/mcp/tools/resolve_semantic_path`: Graph traversal API for field disambiguation
    - **Ground Truth SQL Storage** (`schema/queries/`): Organized SQL files by category with API-key protected save endpoint
    - **Port Configuration**: HF Space runs on port 5000 (public), Flask runs on port 8080 (internal)
    - **Database**: SQLite (`schema/manufacturing.db`) - no external database required for local development
    - **Keywords**: text-to-sql, manufacturing, mcp, github-copilot, semantic-layer, graph-disambiguation
- **Schema Files**:
    - `schema/schema_sqlite.sql`: SQLite-compatible schema (20 tables) for local development
    - `schema/schema.sql`: Original PostgreSQL schema (24 tables) for Replit production
    - `LOCAL_SETUP.md`: Quick start guide for local development with SQLite

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