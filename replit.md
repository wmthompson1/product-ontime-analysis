# Python Educational Script with Flask Application

## Overview

This project features an interactive Python educational script designed to help beginners learn basic programming concepts through engaging examples and hands-on exercises. The project also includes a Flask web application with PostgreSQL database for API endpoints, and an Astro demonstration for JavaScript framework concepts.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **ORM**: SQLAlchemy with Flask-SQLAlchemy extension
- **Database**: PostgreSQL (configured via environment variables)
- **API Design**: RESTful endpoints returning JSON responses

### Application Structure
- **main.py**: Primary Flask application with user management endpoints
- **models.py**: Database model definitions (currently contains User model setup)
- **Supporting Scripts**: Various Python learning exercises and utilities

## Key Components

### Flask Application (main.py)
- Uses Flask-SQLAlchemy for database operations
- Implements declarative base model approach
- Provides user CRUD operations via REST API
- Includes database connection pooling configuration
- Auto-creates database tables on startup

### Database Models
- **User Model**: Basic user entity with id, name, and email fields
- Uses SQLAlchemy's new declarative mapping style with type annotations
- Configured for PostgreSQL with proper connection handling

### API Endpoints
- `GET /`: Basic health check endpoint
- `GET /api/users`: Retrieve all users
- `POST /api/users`: Create new user (endpoint defined but implementation incomplete)

### Configuration
- Database URL from environment variable `DATABASE_URL`
- Flask secret key from environment variable `FLASK_SECRET_KEY`
- Connection pooling with 300-second recycle and pre-ping enabled

## Data Flow

1. **Request Processing**: Flask receives HTTP requests on defined routes
2. **Database Operations**: SQLAlchemy ORM handles database interactions
3. **Response Generation**: JSON responses returned for API endpoints
4. **Connection Management**: Automatic connection pooling and cleanup

## External Dependencies

### Core Dependencies
- **Flask**: Web framework
- **Flask-SQLAlchemy**: Database ORM integration
- **psycopg2-binary**: PostgreSQL database adapter
- **SQLAlchemy**: Object-relational mapping

### Additional Libraries
- **requests**: HTTP client library
- **beautifulsoup4**: HTML parsing
- **lxml**: XML/HTML parsing
- **trafilatura**: Web content extraction

## Deployment Strategy

### Environment Setup
- Python 3.11 runtime environment
- PostgreSQL 16 database server
- Nix package manager for system dependencies

### Configuration Requirements
- `DATABASE_URL`: PostgreSQL connection string
- `FLASK_SECRET_KEY`: Application secret key for sessions
- Default port: 5000 (mapped to external port 80)

### Replit Configuration
- Automatic workflow execution for Flask app
- Port forwarding configured for web access
- Development mode with debug enabled

## Changelog
- June 24, 2025. Initial setup
- July 15, 2025. Comprehensive semantic layer for RAG-assisted SQL implementation with LangChain integration, safety guardrails, and production-ready architecture
- July 28, 2025. Full Astro application development with Teachable Machine framework explanation concept, Flask-Astro API integration with working connection testing
- July 28, 2025. Resolved application startup issues, fixed Vite configuration for Replit hosting, established working Flask-Astro communication with proper CORS and proxy setup

## Recent Major Changes

### Full Astro Application with Framework Education (July 28, 2025)
- **Architecture**: Complete Astro application with file-based routing, component architecture, and React integration
- **Core Components**:
  - `astro-sample/src/layouts/Layout.astro`: Shared layout with navigation and footer
  - `astro-sample/src/pages/index.astro`: Homepage with framework comparison and code examples
  - `astro-sample/src/pages/teachable-machine.astro`: Interactive demo page
  - `astro-sample/src/pages/flask-integration.astro`: Flask connection testing
- **Interactive Features**: 
  - `astro-sample/src/components/TeachableMachineDemo.jsx`: React component simulating 3-step ML workflow
  - `astro-sample/src/components/FlaskConnector.jsx`: Live Flask API connection testing
- **Technical Implementation**: 
  - Vite proxy configuration for seamless Flask API integration
  - CORS handling and Replit domain allowlisting
  - Production-ready Astro configuration with Tailwind CSS
- **Status**: Fully functional with all menu items tested and working correctly

### RAG-Assisted SQL Semantic Layer (July 15, 2025)
- **Architecture**: Built comprehensive semantic layer with schema introspection, safety validation, and query generation
- **Components**: 
  - `app/semantic_layer.py`: LangChain-based NL to SQL conversion with complexity classification
  - `app/schema_context.py`: Dynamic database schema inspection and context generation
  - `app/database_executor.py`: Safe query execution with timeout and monitoring
  - `app/main.py`: FastAPI REST API endpoints for semantic layer services
- **Safety Features**: SQL injection prevention, operation whitelisting, parameter binding enforcement
- **Monitoring**: Query statistics, execution timing, conversation memory, cost tracking
- **Production Ready**: Comprehensive error handling, logging, rate limiting capabilities

## User Preferences

Preferred communication style: Simple, everyday language.
Technical preferences: LangChain for semantic layer, comprehensive safety guardrails for SQL execution, production-ready architecture with monitoring.
JavaScript framework interest: Exploring Astro as modern frontend framework to complement Flask backend, interested in Teachable Machine analogy for understanding framework concepts.
Learning path: Advanced Python for business applications, preparing to work with APIs at aerospace manufacturing company, enrolled in AI learning for Business leaders (Berkeley Haas), needs CSV upload and processing capabilities for work projects.