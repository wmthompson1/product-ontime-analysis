# Flask Application with PostgreSQL Database

## Overview

This is a Flask web application that provides RESTful API endpoints for user management. The application uses SQLAlchemy as the ORM and is configured to work with PostgreSQL database. The project includes various Python learning exercises and utility scripts alongside the main Flask application.

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

## User Preferences

Preferred communication style: Simple, everyday language.