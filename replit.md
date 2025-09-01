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
- **LangGraph 101 Implementation**: Complete Entry Point series (010-015) demonstrating LangGraph base class patterns:
    - Custom manufacturing tools registry system
    - StateGraph workflow orchestration
    - Tool calling loop agent patterns
    - Direct email→manufacturing assistant adaptation following langchain-ai/agents-from-scratch architecture
    - Manufacturing Queue Router system with proper edges/nodes configuration (inbox→queue adaptation)

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